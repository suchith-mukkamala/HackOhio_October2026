"""Project invitation delivery, permissions, and acceptance in an isolated database."""
import unittest
import test_projects
from sqlmodel import select
from app.models import Invite, ProfileSettingsRecord, ProjectMember
from app.routers import invitations


class ProjectInvitationTests(unittest.TestCase):
    def setUp(self):
        test_projects.ProjectPermissionTests.setUp(self)
        self.app.include_router(invitations.router, prefix='/api')

    tearDown = test_projects.ProjectPermissionTests.tearDown

    def send(self, recipient=1):
        response = self.client.post(self.path + f'/invite?to_id={self.users[recipient].id}')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def decide(self, invite, status):
        return self.client.post(f'/api/project-invites/{invite["id"]}/respond', json={'status':status})

    def test_accept_invitation_adds_member_and_edit_access(self):
        invite = self.send()
        self.assertIsNone(self.session.get(ProjectMember, (self.pid, self.users[1].id)))
        self.actor = self.users[1]
        received = self.client.get('/api/project-invites').json()
        self.assertEqual(received[0]['project']['title'], 'Original')
        self.assertNotIn('password_hash', str(received))
        self.assertEqual(self.decide(invite, 'accepted').status_code, 200)
        self.assertEqual(self.decide(invite, 'accepted').status_code, 200)
        self.assertEqual(self.session.get(ProjectMember, (self.pid, self.actor.id)).role, 'member')
        self.assertEqual(self.client.put(self.path, json={'title':'Joined team'}).status_code, 200)
        self.assertEqual(self.client.get(self.path + '/invites').json()[0]['status'], 'accepted')

    def test_decline_does_not_add_member_and_allows_later_new_invite(self):
        invite = self.send()
        self.actor = self.users[1]
        self.assertEqual(self.decide(invite, 'declined').status_code, 200)
        self.assertEqual(self.decide(invite, 'accepted').status_code, 409)
        self.assertIsNone(self.session.get(ProjectMember, (self.pid, self.actor.id)))
        self.assertEqual(self.client.put(self.path, json={'title':'No access'}).status_code, 403)
        self.actor = self.users[0]
        self.assertNotEqual(self.send()['id'], invite['id'])

    def test_permissions_duplicates_and_recipient_only_decision(self):
        invite = self.send()
        self.assertEqual(self.client.post(self.path + f'/invite?to_id={self.users[1].id}').status_code, 409)
        self.assertEqual(self.decide(invite, 'accepted').status_code, 403)
        self.actor = self.users[2]
        self.assertEqual(self.client.get('/api/project-invites').json(), [])
        self.assertEqual(self.client.get(self.path + '/invites').status_code, 403)
        self.assertEqual(self.decide(invite, 'declined').status_code, 403)
        self.assertEqual(self.client.post(self.path + f'/invite?to_id={self.users[3].id}').status_code, 403)

    def test_member_can_invite_but_not_self_owner_or_existing_member(self):
        test_projects.ProjectPermissionTests.add_member(self)
        self.actor = self.users[1]
        self.send(2)
        self.assertEqual(self.client.post(self.path + f'/invite?to_id={self.users[1].id}').status_code, 400)
        self.assertEqual(self.client.post(self.path + f'/invite?to_id={self.users[0].id}').status_code, 409)

    def test_archive_and_preferences_are_enforced(self):
        self.session.add(ProfileSettingsRecord(user_id=self.users[2].id, data={'group_invites':'nobody'}))
        self.session.commit()
        self.assertEqual(self.client.post(self.path + f'/invite?to_id={self.users[2].id}').status_code, 403)
        invite = self.send()
        self.client.post(self.path + '/archive')
        self.assertEqual(self.client.post(self.path + f'/invite?to_id={self.users[3].id}').status_code, 409)
        self.actor = self.users[1]
        self.assertEqual(self.decide(invite, 'accepted').status_code, 409)
        self.assertEqual(self.decide(invite, 'declined').status_code, 200)

    def test_authentication_and_invalid_decision(self):
        invite = self.send()
        self.actor = self.users[1]
        self.assertEqual(self.decide(invite, 'owner').status_code, 422)
        self.assertEqual(len(self.session.exec(select(Invite)).all()), 1)
        del self.app.dependency_overrides[__import__('app.auth',fromlist=['current_user']).current_user]
        self.assertEqual(self.client.get('/api/project-invites').status_code, 401)
        self.assertEqual(self.decide(invite, 'accepted').status_code, 401)
