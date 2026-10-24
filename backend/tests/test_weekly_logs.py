import unittest
from sqlmodel import select
import test_projects
from app.models import Comment, LogEntry, Post, Project


class WeeklyLogTests(unittest.TestCase):
    def setUp(self):
        test_projects.ProjectPermissionTests.setUp(self)
        test_projects.ProjectPermissionTests.add_member(self)
        self.log = LogEntry(project_id=self.pid, author_id=self.users[0].id, title='Original log', week_label='Week 1', commit_shas=['abc'], source='ai')
        self.session.add(self.log); self.session.commit()
        self.lid = self.log.id
        self.post = Post(author_id=self.users[0].id, project_id=self.pid, log_entry_id=self.lid, body='Original log', type='log')
        self.session.add(self.post); self.session.commit()
        self.post_id = self.post.id
        self.session.add(Comment(author_id=self.users[1].id, post_id=self.post_id, body='Feedback'))
        self.session.commit()
        self.url = self.path + f'/logs/{self.lid}'
        self.body = {'title': 'Edited log', 'week_label': 'Week 2', 'built': ['New feature'], 'learned': ['SQL'], 'stuck': [], 'skills': ['Python']}

    tearDown = test_projects.ProjectPermissionTests.tearDown

    def test_author_can_edit_and_feed_stays_in_sync(self):
        response = self.client.put(self.url, json={**self.body, 'author_id': self.users[1].id, 'commit_shas': ['forged'], 'source': 'manual'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['title'], 'Edited log')
        self.assertEqual(response.json()['author_id'], self.users[0].id)
        self.assertEqual(response.json()['commit_shas'], ['abc'])
        self.assertEqual(response.json()['source'], 'ai')
        self.assertEqual(self.session.get(Post, self.post_id).body, 'Edited log')
        self.assertEqual(len(self.session.exec(select(Comment)).all()), 1)

    def test_teammates_and_outsiders_cannot_edit_or_delete_others_logs(self):
        for actor in self.users[1:]:
            self.actor = actor
            self.assertEqual(self.client.put(self.url, json=self.body).status_code, 403)
            self.assertEqual(self.client.delete(self.url).status_code, 403)
        self.assertEqual(self.session.get(LogEntry, self.lid).title, 'Original log')

    def test_author_loses_access_after_leaving(self):
        self.assertEqual(self.client.post(self.path + '/leave').status_code, 204)
        self.assertEqual(self.client.put(self.url, json=self.body).status_code, 403)
        self.assertEqual(self.client.delete(self.url).status_code, 403)

    def test_delete_removes_only_log_and_related_feed_activity(self):
        other = LogEntry(project_id=self.pid, author_id=self.users[1].id, title='Keep', week_label='Week 1')
        self.session.add(other); self.session.commit(); other_id = other.id
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertIsNone(self.session.get(LogEntry, self.lid))
        self.assertIsNone(self.session.get(Post, self.post_id))
        self.assertEqual(self.session.exec(select(Comment)).all(), [])
        self.assertIsNotNone(self.session.get(LogEntry, other_id))
        self.assertIsNotNone(self.session.get(Project, self.pid))

    def test_project_scoping_and_validation(self):
        other = Project(owner_id=self.users[0].id, title='Other')
        self.session.add(other); self.session.commit()
        wrong_url = f'/api/projects/{other.id}/logs/{self.lid}'
        self.assertEqual(self.client.put(wrong_url, json=self.body).status_code, 404)
        self.assertEqual(self.client.delete(wrong_url).status_code, 404)
        self.assertEqual(self.client.put(self.url, json={**self.body, 'title': '   '}).status_code, 422)
        self.assertEqual(self.client.put(self.url, json={**self.body, 'week_label': '   '}).status_code, 422)

    def test_authentication_required(self):
        from app.auth import current_user
        del self.app.dependency_overrides[current_user]
        self.assertEqual(self.client.put(self.url, json=self.body).status_code, 401)
        self.assertEqual(self.client.delete(self.url).status_code, 401)
