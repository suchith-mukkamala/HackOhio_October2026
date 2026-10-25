import unittest
from unittest.mock import patch
import test_messaging
from app.auth import current_user
from app.models import User
from app.routers import admin


class AdminRedeemTests(unittest.TestCase):
    def setUp(self):
        test_messaging.MessagingTests.setUp(self)
        self.app.include_router(admin.router, prefix='/api')
        self.actor.username = 'adi'
        self.actor.name = 'Adi Duggal'
        self.session.add(self.actor); self.session.commit()

    tearDown = test_messaging.MessagingTests.tearDown

    def test_adi_gets_persistent_admin_access_only_with_shared_code(self):
        with patch.object(admin.settings, 'admin_code', 'test-only-shared-code'):
            self.assertEqual(self.client.get('/api/admin/users').status_code, 403)
            self.assertEqual(self.client.post('/api/admin/redeem', json={'code': 'wrong'}).status_code, 403)
            self.assertFalse(self.actor.is_admin)
            response = self.client.post('/api/admin/redeem', json={'code': 'test-only-shared-code'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()['is_admin'])
            uid = self.actor.id
            self.session.expire_all()
            self.assertTrue(self.session.get(User, uid).is_admin)
            self.assertEqual(self.client.get('/api/admin/users').status_code, 200)
            self.assertFalse(self.users[1].is_admin)

    def test_missing_code_does_not_grant_admin(self):
        with patch.object(admin.settings, 'admin_code', ''):
            response = self.client.post('/api/admin/redeem', json={'code': 'anything'})
            self.assertEqual(response.status_code, 404)
            self.assertIn('ADMIN_CODE', response.json()['detail'])
            self.assertFalse(self.actor.is_admin)

    def test_shared_code_requires_signin(self):
        del self.app.dependency_overrides[current_user]
        with patch.object(admin.settings, 'admin_code', 'test-only-shared-code'):
            self.assertEqual(self.client.post('/api/admin/redeem', json={'code': 'test-only-shared-code'}).status_code, 401)
