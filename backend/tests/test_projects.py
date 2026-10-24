import unittest
from sqlalchemy import text
from sqlmodel import select
import test_messaging
from app.models import Comment, Endorsement, HelpRequest, Invite, LogEntry, Post, Project, ProjectMember
from app.routers import projects


class ProjectPermissionTests(unittest.TestCase):
    def setUp(self):
        test_messaging.MessagingTests.setUp(self)
        self.app.include_router(projects.router, prefix='/api')
        self.session.execute(text('PRAGMA foreign_keys=ON'))
        self.project = Project(owner_id=self.users[0].id, title='Original')
        self.session.add(self.project)
        self.session.commit()
        self.pid = self.project.id
        self.session.add(ProjectMember(project_id=self.pid, user_id=self.users[0].id, role='owner'))
        self.session.commit()
        self.path = f'/api/projects/{self.pid}'

    tearDown = test_messaging.MessagingTests.tearDown

    def add_member(self):
        self.session.add(ProjectMember(project_id=self.pid, user_id=self.users[1].id))
        self.session.commit()

    def test_outsider_cannot_change_delete_leave_or_publish(self):
        self.actor = self.users[2]
        self.assertEqual(self.client.put(self.path, json={'title': 'Intrusion'}).status_code, 403)
        self.assertEqual(self.client.delete(self.path).status_code, 403)
        self.assertEqual(self.client.post(self.path + '/leave').status_code, 403)
        self.assertEqual(self.client.post(self.path + '/logs', json={'title': 'Intrusion', 'week_label': 'Now'}).status_code, 403)
        self.assertEqual(self.session.get(Project, self.pid).title, 'Original')

    def test_owner_and_participant_can_edit_without_changing_owner(self):
        self.add_member()
        for actor in self.users[:2]:
            self.actor = actor
            response = self.client.put(self.path, json={'title': 'Updated', 'description': 'Details', 'tags': ['Python'], 'owner_id': self.users[2].id})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['title'], 'Updated')
            self.assertEqual(response.json()['owner_id'], self.users[0].id)
        self.assertEqual(self.client.put(self.path, json={'title': '   '}).status_code, 422)

    def test_group_cannot_be_deleted_and_member_can_leave(self):
        self.add_member()
        self.assertEqual(self.client.delete(self.path).status_code, 409)
        self.actor = self.users[1]
        self.assertEqual(self.client.delete(self.path).status_code, 403)
        self.assertEqual(self.client.post(self.path + '/leave').status_code, 204)
        self.assertIsNotNone(self.session.get(Project, self.pid))
        self.assertEqual(self.client.put(self.path, json={'title': 'No longer allowed'}).status_code, 403)

    def test_owner_leaving_transfers_ownership(self):
        self.add_member()
        self.assertEqual(self.client.post(self.path + '/leave').status_code, 204)
        project = self.session.get(Project, self.pid)
        self.assertEqual(project.owner_id, self.users[1].id)
        self.assertEqual(self.session.get(ProjectMember, (self.pid, self.users[1].id)).role, 'owner')
        self.assertIsNone(self.session.get(ProjectMember, (self.pid, self.users[0].id)))
        self.assertEqual(self.client.put(self.path, json={'title': 'Old owner'}).status_code, 403)
        self.assertEqual(self.client.delete(self.path).status_code, 403)

    def test_solo_owner_must_delete_and_dependencies_are_cleaned(self):
        self.assertEqual(self.client.post(self.path + '/leave').status_code, 409)
        log = LogEntry(project_id=self.pid, author_id=self.users[0].id, title='Log', week_label='Now')
        help_request = HelpRequest(project_id=self.pid, requester_id=self.users[0].id, question='Help')
        self.session.add_all([log, help_request]); self.session.commit()
        post = Post(author_id=self.users[0].id, project_id=self.pid, log_entry_id=log.id, body='Log')
        self.session.add(post); self.session.commit()
        self.session.add_all([
            Comment(author_id=self.users[1].id, post_id=post.id, body='Feedback'),
            Comment(author_id=self.users[1].id, project_id=self.pid, body='Feedback'),
            Endorsement(from_id=self.users[1].id, to_id=self.users[0].id, skill='Python', help_request_id=help_request.id),
            Invite(project_id=self.pid, from_id=self.users[0].id, to_id=self.users[1].id),
        ]); self.session.commit()
        other = Project(owner_id=self.users[2].id, title='Keep me')
        self.session.add(other); self.session.commit(); other_id = other.id
        response = self.client.delete(self.path)
        self.assertEqual(response.status_code, 204, response.text)
        for model in [LogEntry, HelpRequest, Comment, Endorsement, Invite, Post, ProjectMember]:
            self.assertEqual(self.session.exec(select(model)).all(), [])
        self.assertIsNone(self.session.get(Project, self.pid))
        self.assertIsNotNone(self.session.get(Project, other_id))

    def test_authentication_required(self):
        from app.auth import current_user
        del self.app.dependency_overrides[current_user]
        self.assertEqual(self.client.put(self.path, json={'title': 'Test'}).status_code, 401)
        self.assertEqual(self.client.delete(self.path).status_code, 401)
        self.assertEqual(self.client.post(self.path + '/leave').status_code, 401)
