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

    def test_expand_existing_network_to_ten_per_role(self):
        seed(self.session, self.users[0].id)
        self.session.commit()
        original_ids = {row.id for row in self.session.exec(select(ConnectionRequest)).all()}
        counts = seed(self.session, self.users[0].id, per_role=10)
        self.session.commit()
        self.assertEqual(counts, dict(users=15, connections=345, threads=345, messages=345))
        requests = self.session.exec(select(ConnectionRequest)).all()
        self.assertEqual(len(requests), 465)
        self.assertTrue(original_ids <= {row.id for row in requests})
        person_ids = {row.sender_id for row in requests} | {row.recipient_id for row in requests}
        self.assertEqual(len(person_ids), 31)
        for person_id in person_ids:
            self.assertEqual(sum(person_id in (row.sender_id, row.recipient_id) for row in requests), 30)
        self.assertTrue(all(value == 0 for value in seed(self.session, self.users[0].id, per_role=10).values()))
