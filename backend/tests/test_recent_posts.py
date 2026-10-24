import unittest
from datetime import datetime, timedelta, timezone
import test_messaging
from app.models import LogEntry, Post, Project


class RecentPostsTests(unittest.TestCase):
    setUp = test_messaging.MessagingTests.setUp
    tearDown = test_messaging.MessagingTests.tearDown

    def test_only_requested_author_newest_first_with_limit(self):
        older = datetime(2026, 1, 1, tzinfo=timezone.utc)
        posts = [Post(author_id=self.users[0].id, body=f'Update {i}', created_at=older + timedelta(days=i)) for i in range(7)]
        self.session.add_all(posts)
        self.session.add(Post(author_id=self.users[1].id, body='Other author', created_at=older + timedelta(days=10)))
        self.session.commit()
        response = self.client.get(f'/api/users/{self.users[0].id}/posts')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['post']['body'] for item in response.json()], [f'Update {i}' for i in range(6, 1, -1)])
        self.assertEqual(len(self.client.get(f'/api/users/{self.users[0].id}/posts?limit=2').json()), 2)
        self.assertNotIn('password_hash', response.text)
        self.assertNotIn('github_token', response.text)

    def test_published_logs_included_and_drafts_excluded_before_limit(self):
        project = Project(owner_id=self.users[0].id, title='Project')
        self.session.add(project); self.session.commit()
        for published in [True, False]:
            log = LogEntry(project_id=project.id, author_id=self.users[0].id, title='Visible' if published else 'Private draft', week_label='Week 1', published=published)
            self.session.add(log); self.session.commit()
            self.session.add(Post(author_id=self.users[0].id, project_id=project.id, log_entry_id=log.id, body=log.title, type='log'))
            self.session.commit()
        result = self.client.get(f'/api/users/{self.users[0].id}/posts?limit=1').json()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['log']['title'], 'Visible')
        self.assertEqual(result[0]['project']['id'], project.id)

    def test_empty_unknown_user_and_invalid_limits(self):
        path = f'/api/users/{self.users[0].id}/posts'
        self.assertEqual(self.client.get(path).json(), [])
        self.assertEqual(self.client.get('/api/users/999999/posts').status_code, 404)
        for limit in ['0', '-1', '21', 'invalid']:
            self.assertEqual(self.client.get(path + '?limit=' + limit).status_code, 422)

    def test_equal_timestamps_have_stable_order(self):
        now = datetime.now(timezone.utc)
        for body in ['First', 'Second']:
            self.session.add(Post(author_id=self.users[0].id, body=body, created_at=now))
        self.session.commit()
        result = self.client.get(f'/api/users/{self.users[0].id}/posts').json()
        self.assertEqual([item['post']['body'] for item in result], ['Second', 'First'])
