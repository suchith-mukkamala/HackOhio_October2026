"""Messaging API checks using an isolated database, never the configured server."""
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
from app.models import Message, Thread, ThreadMember, User
from app.routers import social


class MessagingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.users = [User(name=name) for name in ['Alex', 'Alex', 'Casey', 'Outside']]
        self.session.add_all(self.users)
        self.session.commit()
        for user in self.users:
            self.session.refresh(user)
        self.actor = self.users[0]
        self.app = FastAPI()
        self.app.include_router(social.router, prefix='/api')
        self.app.dependency_overrides[get_session] = lambda: self.session
        self.app.dependency_overrides[current_user] = lambda: self.actor
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.session.close()
        self.engine.dispose()

    def create(self, ids):
        response = self.client.post('/api/threads', json={'user_ids': ids})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['id']

    def test_direct_and_group_are_distinct_and_reused(self):
        a, b, c, _ = [u.id for u in self.users]
        group = self.create([b, c, b, a])
        direct = self.create([b])
        self.assertNotEqual(group, direct)
        self.assertEqual(self.create([c, b]), group)
        self.assertEqual(self.create([b]), direct)
        self.actor = self.users[1]
        self.assertEqual(self.create([a]), direct)
        self.assertEqual(self.client.post(f'/api/threads?user_id={a}').json()['id'], direct)
        threads = self.client.get('/api/threads').json()
        self.assertEqual({t['id'] for t in threads}, {group, direct})
        self.assertEqual(len(next(t for t in threads if t['id'] == group)['with']), 2)
        self.assertNotIn('password_hash', str(threads))
        self.assertNotIn('github_token', str(threads))

    def test_send_persists_for_every_member_and_updates_preview(self):
        tid = self.create([self.users[1].id, self.users[2].id])
        response = self.client.post(f'/api/threads/{tid}/messages', json={'body': '  Hello group!  '})
        self.assertEqual(response.status_code, 200, response.text)
        message = response.json()
        self.assertEqual(message['body'], 'Hello group!')
        self.assertEqual(message['sender_id'], self.users[0].id)
        self.assertEqual(self.session.exec(select(Message)).one().body, 'Hello group!')
        for actor in self.users[:3]:
            self.actor = actor
            self.assertEqual(self.client.get(f'/api/threads/{tid}/messages').json(), [message])
            self.assertEqual(self.client.get('/api/threads').json()[0]['last'], message)

    def test_nonmembers_cannot_read_or_send(self):
        tid = self.create([self.users[1].id])
        self.actor = self.users[3]
        self.assertEqual(self.client.get('/api/threads').json(), [])
        self.assertEqual(self.client.get(f'/api/threads/{tid}/messages').status_code, 403)
        self.assertEqual(self.client.post(f'/api/threads/{tid}/messages', json={'body': 'intrusion'}).status_code, 403)
        self.assertEqual(self.session.exec(select(Message)).all(), [])

    def test_invalid_recipients_and_messages_leave_no_partial_data(self):
        for body in [{'user_ids': []}, {'user_ids': [self.users[0].id]}, {'user_ids': [9999]}, {'user_ids': [self.users[1].id, 9999]}]:
            self.assertIn(self.client.post('/api/threads', json=body).status_code, [400, 404, 422])
        self.assertEqual(self.session.exec(select(Thread)).all(), [])
        self.assertEqual(self.session.exec(select(ThreadMember)).all(), [])
        tid = self.create([self.users[1].id])
        for body in ['', '   ', 'x' * 10001]:
            self.assertEqual(self.client.post(f'/api/threads/{tid}/messages', json={'body': body}).status_code, 422)
        self.assertEqual(self.session.exec(select(Message)).all(), [])

    def test_authentication_required(self):
        del self.app.dependency_overrides[current_user]
        self.assertEqual(self.client.get('/api/threads').status_code, 401)
        self.assertEqual(self.client.post('/api/threads', json={'user_ids': [1]}).status_code, 401)
        self.assertEqual(self.client.get('/api/threads/1/messages').status_code, 401)
        self.assertEqual(self.client.post('/api/threads/1/messages', json={'body': 'hi'}).status_code, 401)
