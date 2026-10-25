"""Sample network integrity; uses an isolated in-memory database."""
import unittest
import test_connections
from sqlmodel import select
from app.models import ConnectionRequest, Message, ThreadMember, User
from seed_connections import seed


class ConnectionSampleTests(unittest.TestCase):
    setUp = test_connections.ConnectionsTests.setUp
    tearDown = test_connections.ConnectionsTests.tearDown

    def test_full_network_is_complete_and_idempotent(self):
        counts = seed(self.session, self.users[0].id)
        self.session.commit()
        self.assertEqual(counts, dict(users=15, connections=120, threads=120, messages=120))
        requests = self.session.exec(select(ConnectionRequest)).all()
        self.assertTrue(all(request.status == 'accepted' for request in requests))
        for person_id in {request.sender_id for request in requests} | {request.recipient_id for request in requests}:
            self.assertEqual(sum(person_id in (request.sender_id, request.recipient_id) for request in requests), 15)
        self.assertEqual(len(self.session.exec(select(ThreadMember)).all()), 240)
        self.assertTrue(all(value == 0 for value in seed(self.session, self.users[0].id).values()))
        self.assertEqual(len(self.session.exec(select(Message)).all()), 120)
        samples = self.session.exec(select(User).where(User.email.like('%@connections.keystone.test'))).all()
        self.assertEqual(len(samples), 15)
        self.assertTrue(all(not user.password_hash and not user.github_token and not user.is_admin for user in samples))

    def test_reserved_name_does_not_replace_real_person(self):
        real = User(username='faculty3', name='Real person', email='real@example.com', password_hash='keep')
        self.session.add(real)
        self.session.commit()
        with self.assertRaises(RuntimeError):
            seed(self.session, self.users[0].id)
        self.session.rollback()
        self.assertEqual(self.session.get(User, real.id).password_hash, 'keep')
        self.assertEqual(self.session.exec(select(ConnectionRequest)).all(), [])
