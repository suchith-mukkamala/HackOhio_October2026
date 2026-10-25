"""Connection consent and message delivery checks against an isolated database."""
import os
import unittest

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['JWT_SECRET'] = 'isolated-test-signing-key-at-least-32-bytes'

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select
from app.auth import current_user
from app.db import get_session
from app.models import ConnectionRequest, Message, ProfileSettingsRecord, Thread, ThreadMember, User
from app.routers import connections, social


class ConnectionsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.users = [User(name='Student', role='student', password_hash='private'), User(name='Mentor', role='mentor', github_token='private'), User(name='Faculty', role='faculty')]
        self.session.add_all(self.users)
        self.session.commit()
        for user in self.users:
            self.session.refresh(user)
        self.actor = self.users[0]
        app = FastAPI()
        app.include_router(connections.router, prefix='/api')
        app.include_router(social.router, prefix='/api')
        app.dependency_overrides[get_session] = lambda: self.session
        app.dependency_overrides[current_user] = lambda: self.actor
        self.app = app
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.session.close()
        self.engine.dispose()

    def request(self):
        response = self.client.post(f'/api/connections/users/{self.users[1].id}')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def respond(self, request, status):
        return self.client.post(f'/api/connections/requests/{request["id"]}/respond', json={'status': status})

    def test_request_delivered_once_and_reverse_request_does_not_accept(self):
        request = self.request()
        self.assertEqual(request['status'], 'pending')
        self.assertEqual(self.request()['id'], request['id'])
        self.assertEqual(len(self.session.exec(select(Message)).all()), 1)
        self.assertEqual(self.client.get('/api/connections').json()['connections'], [])
        sender_messages = self.client.get(f'/api/threads/{request["thread_id"]}/messages').json()
        self.assertEqual(sender_messages[0]['follow_request']['status'], 'pending')
        self.assertEqual(sender_messages[0]['body'], 'Requested to follow.')
        self.actor = self.users[1]
        reverse = self.client.post(f'/api/connections/users/{self.users[0].id}').json()
        self.assertEqual(reverse['id'], request['id'])
        self.assertEqual(reverse['status'], 'pending')
        incoming = self.client.get('/api/connections').json()['requests'][0]
        self.assertEqual(incoming['sender_id'], self.users[0].id)
        self.assertEqual(incoming['user']['name'], 'Student')

    def test_accept_connects_both_people_and_updates_original_message(self):
        request = self.request()
        self.actor = self.users[1]
        response = self.respond(request, 'accepted')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNotNone(response.json()['responded_at'])
        self.assertEqual(self.respond(request, 'accepted').status_code, 200)
        recipient = self.client.get('/api/connections').json()
        self.assertEqual([u['id'] for u in recipient['connections']], [self.users[0].id])
        self.assertEqual(recipient['requests'], [])
        self.actor = self.users[0]
        sender = self.client.get('/api/connections').json()
        self.assertEqual([u['id'] for u in sender['connections']], [self.users[1].id])
        self.assertNotIn('github_token', str(sender))
        self.assertNotIn('password_hash', str(sender))
        messages = self.client.get(f'/api/threads/{request["thread_id"]}/messages').json()
        self.assertEqual(messages[0]['follow_request']['status'], 'accepted')
        preview = self.client.get('/api/threads').json()[0]['last']
        self.assertIn('accepted', preview['body'])
        self.assertEqual(preview['follow_request']['status'], 'accepted')

    def test_deny_visible_to_sender_and_cannot_be_reversed_or_spammed(self):
        request = self.request()
        self.actor = self.users[1]
        self.assertEqual(self.respond(request, 'denied').status_code, 200)
        self.assertEqual(self.respond(request, 'denied').status_code, 200)
        self.assertEqual(self.respond(request, 'accepted').status_code, 409)
        self.actor = self.users[0]
        result = self.client.get('/api/connections').json()
        self.assertEqual(result['connections'], [])
        self.assertEqual(result['requests'][0]['status'], 'denied')
        self.assertEqual(self.request()['status'], 'denied')
        self.assertEqual(len(self.session.exec(select(Message)).all()), 1)
        self.assertIn('denied', self.client.get('/api/threads').json()[0]['last']['body'])

    def test_only_recipient_can_decide_and_outsider_cannot_read_request(self):
        request = self.request()
        self.assertEqual(self.respond(request, 'accepted').status_code, 403)
        self.actor = self.users[2]
        self.assertEqual(self.respond(request, 'denied').status_code, 403)
        self.assertEqual(self.client.get(f'/api/threads/{request["thread_id"]}/messages').status_code, 403)
        self.assertEqual(self.client.get('/api/connections').json(), {'connections': [], 'requests': [], 'interconnections': []})
        self.assertEqual(self.client.get(f'/api/connections/users/{self.users[0].id}').json(), None)

    def test_reuses_direct_thread_never_group(self):
        group = self.client.post('/api/threads', json={'user_ids': [u.id for u in self.users[1:]]}).json()['id']
        direct = self.client.post('/api/threads', json={'user_ids': [self.users[1].id]}).json()['id']
        request = self.request()
        self.assertEqual(request['thread_id'], direct)
        self.assertNotEqual(request['thread_id'], group)
        self.assertEqual(self.client.get(f'/api/threads/{group}/messages').json(), [])

    def test_respects_contact_preferences_and_validates_input(self):
        self.session.add(ProfileSettingsRecord(user_id=self.users[1].id, data={'direct_messages': 'nobody'}))
        self.session.commit()
        self.assertEqual(self.client.post(f'/api/connections/users/{self.users[1].id}').status_code, 403)
        self.assertEqual(self.client.post(f'/api/connections/users/{self.users[0].id}').status_code, 400)
        self.assertEqual(self.client.post('/api/connections/users/99999').status_code, 404)
        self.assertEqual(self.client.post('/api/connections/requests/99999/respond', json={'status': 'accepted'}).status_code, 404)
        self.assertEqual(self.client.post('/api/connections/requests/1/respond', json={'status': 'pending'}).status_code, 422)
        self.assertEqual(self.session.exec(select(ConnectionRequest)).all(), [])
        self.assertEqual(self.session.exec(select(Thread)).all(), [])
        self.assertEqual(self.session.exec(select(Message)).all(), [])

    def test_auth_required(self):
        del self.app.dependency_overrides[current_user]
        for method, path, body in [('get', '/api/connections', None), ('get', '/api/connections/users/1', None), ('post', '/api/connections/users/1', None), ('post', '/api/connections/requests/1/respond', {'status': 'accepted'})]:
            response = getattr(self.client, method)(path, **({'json': body} if body else {}))
            self.assertEqual(response.status_code, 401, response.text)

    def test_interconnections_only_include_accepted_visible_endpoints(self):
        a, b, c = self.users
        def connect(sender, recipient, status='accepted'):
            self.actor = sender
            request = self.client.post(f'/api/connections/users/{recipient.id}').json()
            if status != 'pending':
                self.actor = recipient
                self.assertEqual(self.respond(request, status).status_code, 200)
            return request
        connect(a, b)
        connect(b, c)
        self.actor = a
        self.assertEqual(self.client.get('/api/connections').json()['interconnections'], [])
        request = connect(a, c, 'pending')
        self.actor = a
        self.assertEqual(self.client.get('/api/connections').json()['interconnections'], [])
        self.actor = c
        self.respond(request, 'accepted')
        self.actor = a
        self.assertEqual(self.client.get('/api/connections').json()['interconnections'], [{'source': min(b.id, c.id), 'target': max(b.id, c.id)}])


if __name__ == '__main__':
    unittest.main()
