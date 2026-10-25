import unittest
from datetime import datetime, timezone
from collections import Counter
import test_messaging
from sqlmodel import select
from app.models import User, Project, ProjectMember, Post, Comment, LogEntry
from app.services.skills import SKILLS
import seed_expanded


class ExpandedSampleTests(unittest.TestCase):
    setUp=test_messaging.MessagingTests.setUp
    tearDown=test_messaging.MessagingTests.tearDown

    def test_complete_seed_is_balanced_relevant_and_idempotent(self):
        initial_users=len(self.session.exec(select(User)).all())
        now=datetime(2026,10,24,18,tzinfo=timezone.utc)
        counts=seed_expanded.seed(self.session,now);self.session.commit()
        self.assertEqual(counts,dict(users=12,projects=3,memberships=12,posts=15,comments=24,logs=3,settings=12))
        people=self.session.exec(select(User).where(User.username.in_([person['username'] for person in seed_expanded.PEOPLE]))).all()
        self.assertEqual(Counter(person.role for person in people),{'student':6,'faculty':3,'mentor':3})
        self.assertTrue(all(not person.password_hash and not person.github_token and not person.is_admin for person in people))
        self.assertTrue(all(set(person.expertise_tags)<=set(SKILLS) for person in people))
        self.assertEqual(len(self.session.exec(select(Project).where(Project.status=='archived')).all()),1)
        posts=self.session.exec(select(Post)).all()
        self.assertEqual(Counter(post.media_kind for post in posts),{None:6,'image':6,'video':3})
        for post in posts:
            self.assertIsNotNone(post.project_id)
            if post.media_url:
                self.assertTrue(post.media_url.startswith(('data:image/','data:video/')))
            if post.media_kind=='video':
                self.assertIn('simulated',post.body.lower())
        again=seed_expanded.seed(self.session,now);self.session.commit()
        self.assertTrue(all(value==0 for value in again.values()),again)
        self.assertEqual(len(self.session.exec(select(User)).all()),initial_users+12)

    def test_reserved_username_cannot_overwrite_real_account(self):
        real=User(username='sample_naomi',name='Real user',email='real@example.com',password_hash='do-not-touch')
        self.session.add(real);self.session.commit()
        with self.assertRaises(RuntimeError):seed_expanded.seed(self.session)
        self.session.rollback()
        self.assertEqual(self.session.get(User,real.id).password_hash,'do-not-touch')
        self.assertEqual(self.session.exec(select(Project)).all(),[])
