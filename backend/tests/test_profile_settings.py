import unittest
from unittest.mock import patch, Mock
import test_messaging
from app.auth import current_user, optional_user
from app.config import settings as config
from app.models import Experience, Post, ProfileSettingsRecord, Project, ProjectMember, User
from app.routers import auth, settings, users
from app.services.profile_settings import Preferences, preferences


class ProfileSettingsTests(unittest.TestCase):
    def setUp(self):
        test_messaging.MessagingTests.setUp(self)
        self.app.include_router(settings.router, prefix='/api')
        self.app.include_router(users.router, prefix='/api')
        self.app.include_router(auth.router, prefix='/api')
        self.app.dependency_overrides[optional_user] = lambda: self.actor

    tearDown = test_messaging.MessagingTests.tearDown

    def payload(self, **prefs):
        return {'profile': {'name': 'Profile Owner', 'bio': 'Building things', 'major': 'CSE', 'avatar_url': 'https://example.com/avatar.png'}, 'preferences': {**Preferences().model_dump(), **prefs}}

    def save(self, **prefs):
        response = self.client.put('/api/me/settings', json=self.payload(**prefs))
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def test_save_profile_and_preferences_are_persistent_and_owner_only(self):
        self.save(availability='teammates', hours_per_week=8, interests=['Robotics'], particles=False, reduce_motion=True)
        result = self.client.get('/api/me/settings').json()
        self.assertEqual(result['user']['name'], 'Profile Owner')
        self.assertEqual(result['preferences']['hours_per_week'], 8)
        self.assertFalse(result['preferences']['particles'])
        self.actor = self.users[1]
        self.assertEqual(self.client.get('/api/me/settings').json()['preferences']['hours_per_week'], 0)
        self.assertNotIn('password_hash', str(result))
        self.assertNotIn('github_token', str(result))

    def test_privacy_is_enforced_for_other_viewers_and_feed(self):
        owner = self.actor
        owner.github_username = 'private-handle'
        self.session.add(owner)
        self.session.add(Experience(user_id=owner.id, kind='work', title='Private job', org='Private employer', skills=['Python']))
        self.session.add(Post(author_id=owner.id, body='Private update'))
        self.session.commit()
        self.save(show_experience=False, show_activity=False, show_contact=False, website='https://example.com', contact_email='private@example.com')
        self.assertEqual(len(self.client.get(f'/api/users/{owner.id}').json()['experience']), 1)
        self.assertEqual(len(self.client.get(f'/api/users/{owner.id}/posts').json()), 1)
        self.actor = self.users[1]
        profile = self.client.get(f'/api/users/{owner.id}').json()
        self.assertEqual(profile['experience'], [])
        self.assertIsNone(profile['user']['github_username'])
        self.assertEqual(profile['preferences']['contact_email'], '')
        self.assertEqual(profile['preferences']['website'], '')
        self.assertEqual(self.client.get(f'/api/users/{owner.id}/posts').json(), [])
        self.assertEqual(self.client.get('/api/feed').json(), [])
        graph = self.client.get(f'/api/users/{owner.id}/skills').json()
        self.assertNotIn('Private employer', str(graph))
        self.assertNotIn('private-handle', self.client.get('/api/search').text)

    def test_pins_only_allow_participating_projects_and_own_posts(self):
        project = Project(owner_id=self.users[1].id, title='Other project')
        other_post = Post(author_id=self.users[1].id, body='Other post')
        self.session.add_all([project, other_post]); self.session.commit()
        self.assertEqual(self.client.put('/api/me/settings', json=self.payload(pinned_project_ids=[project.id])).status_code, 403)
        self.assertEqual(self.client.put('/api/me/settings', json=self.payload(pinned_post_id=other_post.id)).status_code, 403)
        self.session.add(ProjectMember(project_id=project.id, user_id=self.actor.id))
        old = Post(author_id=self.actor.id, body='Pinned')
        new = Post(author_id=self.actor.id, body='Newest')
        self.session.add_all([old, new]); self.session.commit()
        self.save(pinned_project_ids=[project.id], pinned_post_id=old.id)
        self.assertEqual(self.client.get(f'/api/users/{self.actor.id}/posts?limit=1').json()[0]['post']['id'], old.id)

    def test_messaging_rules_block_direct_and_group_creation(self):
        sender = self.actor
        self.actor = self.users[1]
        self.save(direct_messages='nobody', group_invites='nobody')
        self.actor = sender
        self.assertEqual(self.client.post('/api/threads', json={'user_ids': [self.users[1].id]}).status_code, 403)
        self.assertEqual(self.client.post('/api/threads', json={'user_ids': [self.users[1].id, self.users[2].id]}).status_code, 403)

    def test_teammates_rule_requires_shared_membership(self):
        sender = self.actor
        self.actor = self.users[1]
        self.save(direct_messages='teammates')
        self.actor = sender
        self.assertEqual(self.client.post('/api/threads', json={'user_ids': [self.users[1].id]}).status_code, 403)
        project = Project(owner_id=sender.id, title='Shared')
        self.session.add(project); self.session.commit()
        self.session.add(ProjectMember(project_id=project.id, user_id=self.users[1].id)); self.session.commit()
        self.assertEqual(self.client.post('/api/threads', json={'user_ids': [self.users[1].id]}).status_code, 200)

    def test_experience_cannot_be_edited_or_removed_by_another_user(self):
        entry = Experience(user_id=self.users[1].id, kind='work', title='Work', org='Team')
        self.session.add(entry); self.session.commit()
        body = {'kind': 'work', 'title': 'Edited', 'org': 'Team', 'skills': ['Python']}
        self.assertEqual(self.client.put(f'/api/me/experience/{entry.id}', json=body).status_code, 404)
        self.assertEqual(self.client.delete(f'/api/me/experience/{entry.id}').status_code, 404)
        self.actor = self.users[1]
        self.assertEqual(self.client.put(f'/api/me/experience/{entry.id}', json=body).status_code, 200)
        self.assertEqual(self.client.delete('/api/me/resume').status_code, 204)
        self.assertIsNone(self.session.get(Experience, entry.id))

    def test_password_change_verifies_old_password_and_preserves_signin_method(self):
        user = self.actor
        user.username = 'builder'; user.password_hash = auth.password_hasher.hash('original-password-long')
        user.github_username = 'builder'; user.github_token = 'secret'
        self.session.add(user); self.session.commit()
        body = {'username': 'builder', 'current_password': 'wrong', 'new_password': 'replacement-password-long'}
        self.assertEqual(self.client.put('/api/me/password', json=body).status_code, 403)
        body['current_password'] = 'original-password-long'
        self.assertEqual(self.client.put('/api/me/password', json=body).status_code, 204)
        self.assertTrue(auth.password_hasher.verify(body['new_password'], user.password_hash))
        self.assertEqual(self.client.delete('/api/me/connections/github').status_code, 204)
        self.actor = self.users[1]
        self.actor.github_token = 'other-secret'
        self.session.add(self.actor); self.session.commit()
        self.assertEqual(self.client.delete('/api/me/connections/github').status_code, 409)

    def test_google_link_signin_and_disconnect(self):
        owner = self.actor
        info = {'sub': 'google-123', 'email': 'google@example.com', 'email_verified': True, 'name': 'Google User'}
        token = Mock(); token.raise_for_status.return_value.json.return_value = {'access_token': 'secret'}
        userinfo = Mock(); userinfo.raise_for_status.return_value.json.return_value = info
        self.client.cookies.set('oauth_state', 'test-state')
        with patch.object(auth.httpx, 'post', return_value=token), patch.object(auth.httpx, 'get', return_value=userinfo):
            response = self.client.get('/api/auth/google/callback?code=code&state=test-state', follow_redirects=False)
            self.assertEqual(response.status_code, 307, response.text)
            record = self.session.get(ProfileSettingsRecord, owner.id)
            self.assertEqual(record.google_sub, 'google-123')
            self.app.dependency_overrides[optional_user] = lambda: None
            response = self.client.get('/api/auth/google/callback?code=code&state=test-state', follow_redirects=False)
            self.assertEqual(response.status_code, 307, response.text)
        self.assertEqual(self.client.delete('/api/me/connections/google').status_code, 409)
        owner.github_token = 'github-token'; self.session.add(owner); self.session.commit()
        self.assertEqual(self.client.delete('/api/me/connections/google').status_code, 204)
        self.assertIsNone(self.session.get(ProfileSettingsRecord, owner.id).google_sub)

    def test_invalid_settings_do_not_change_profile(self):
        for prefs in [{'website': 'javascript:alert(1)'}, {'linkedin': 'http://example.com'}, {'hours_per_week': 81}, {'highlighted_skills': ['Unknown']}, {'highlighted_skills': ['Python']}]:
            self.assertEqual(self.client.put('/api/me/settings', json=self.payload(**prefs)).status_code, 422)
        self.assertEqual(self.actor.name, 'Alex')
        self.actor.expertise_tags = ['Python']; self.session.add(self.actor); self.session.commit()
        self.save(highlighted_skills=['Python'])
        self.assertEqual(preferences(self.session, self.actor.id).highlighted_skills, ['Python'])

    def test_settings_require_signin(self):
        del self.app.dependency_overrides[current_user]
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/me/settings').status_code, 401)
        self.assertEqual(self.client.put('/api/me/settings', json=self.payload()).status_code, 401)
