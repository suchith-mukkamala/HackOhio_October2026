import unittest
from datetime import date
import test_projects
from app.auth import current_user
from app.models import LogEntry, Project, ProjectMember
from app.routers import help as help_routes


class ProjectShowcaseTests(unittest.TestCase):
    def setUp(self):
        test_projects.ProjectPermissionTests.setUp(self)
        self.app.include_router(help_routes.router, prefix='/api')

    tearDown = test_projects.ProjectPermissionTests.tearDown

    def test_completion_preserves_team_logs_and_sets_end_date(self):
        test_projects.ProjectPermissionTests.add_member(self)
        log = LogEntry(project_id=self.pid, author_id=self.actor.id, title='Final build', week_label='Final week')
        draft = LogEntry(project_id=self.pid, author_id=self.actor.id, title='Private draft', week_label='Draft', published=False)
        self.session.add_all([log, draft]); self.session.commit()
        result = self.client.post(self.path + '/archive')
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['status'], 'archived')
        self.assertEqual(result.json()['end_date'], date.today().isoformat())
        detail = self.client.get(self.path).json()
        self.assertEqual(len(detail['members']), 2)
        self.assertEqual([row['title'] for row in detail['timeline']], ['Final build'])
        self.assertEqual([row['title'] for row in self.client.get(self.path + '/logs').json()], ['Final build'])
        self.assertIsNotNone(self.session.get(LogEntry, draft.id))
        self.assertEqual(self.client.post(self.path + '/archive').json()['end_date'], date.today().isoformat())

    def test_only_owner_can_complete_or_reopen_even_in_group(self):
        test_projects.ProjectPermissionTests.add_member(self)
        for actor in self.users[1:]:
            self.actor = actor
            self.assertEqual(self.client.post(self.path + '/archive').status_code, 403)
            self.assertEqual(self.client.post(self.path + '/reopen').status_code, 403)
        self.assertEqual(self.session.get(Project, self.pid).status, 'active')

    def test_completed_projects_are_public_and_discoverable(self):
        self.assertEqual(self.client.post(self.path + '/archive').status_code, 200)
        active = Project(owner_id=self.actor.id, title='Still building')
        self.session.add(active); self.session.commit()
        del self.app.dependency_overrides[current_user]
        response = self.client.get('/api/projects?status=archived')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()], [self.pid])
        detail = self.client.get(self.path)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['project']['status'], 'archived')
        self.assertNotIn(self.pid, [item['id'] for item in self.client.get('/api/projects').json()])

    def test_archived_project_rejects_new_work_until_reopened(self):
        self.client.post(self.path + '/archive')
        log = {'title': 'New work', 'week_label': 'Next week'}
        self.assertEqual(self.client.post(self.path + '/logs', json=log).status_code, 409)
        self.assertEqual(self.client.post(self.path + '/logs/draft').status_code, 409)
        self.assertEqual(self.client.post(self.path + '/invite', params={'to_id': self.users[1].id}).status_code, 409)
        self.assertEqual(self.client.post('/api/help', json={'project_id': self.pid, 'question': 'New help'}).status_code, 409)
        reopened = self.client.post(self.path + '/reopen')
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(reopened.json()['status'], 'active')
        self.assertIsNone(reopened.json()['end_date'])
        self.assertEqual(self.client.get('/api/projects?status=archived').json(), [])
        self.assertEqual(self.client.post(self.path + '/logs', json=log).status_code, 200)

    def test_archived_project_does_not_bypass_edit_delete_permissions(self):
        test_projects.ProjectPermissionTests.add_member(self)
        self.client.post(self.path + '/archive')
        self.assertEqual(self.client.delete(self.path).status_code, 409)
        self.actor = self.users[2]
        self.assertEqual(self.client.put(self.path, json={'title': 'Intrusion'}).status_code, 403)
        self.assertEqual(self.client.delete(self.path).status_code, 403)

    def test_completion_requires_authentication(self):
        del self.app.dependency_overrides[current_user]
        self.assertEqual(self.client.post(self.path + '/archive').status_code, 401)
        self.assertEqual(self.client.post(self.path + '/reopen').status_code, 401)
