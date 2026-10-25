"""Check requested account cleanup with foreign keys enabled in an isolated database."""
import unittest
from datetime import datetime, timezone
import test_projects
from sqlmodel import select
from app.models import (User, Project, ProjectMember, LogEntry, Post, Comment, HelpRequest,
    Endorsement, Challenge, Thread, ThreadMember, Message, ConnectionRequest, ProfileSettingsRecord)
from remove_requested_users import cleanup


class RequestedCleanupTests(unittest.TestCase):
    setUp = test_projects.ProjectPermissionTests.setUp
    tearDown = test_projects.ProjectPermissionTests.tearDown

    def test_dependencies_removed_and_unrelated_work_preserved(self):
        keep, target, other_target, teammate = self.users
        project = Project(owner_id=target.id, title='Remove owned project')
        self.session.add(project); self.session.flush()
        self.session.add(ProjectMember(project_id=project.id,user_id=teammate.id))
        log = LogEntry(project_id=self.pid,author_id=target.id,week_label='Week 1',title='Remove log')
        self.session.add(log); self.session.flush()
        post = Post(author_id=target.id,project_id=self.pid,log_entry_id=log.id,body='Remove post')
        self.session.add(post); self.session.flush()
        self.session.add(Comment(author_id=keep.id,post_id=post.id,body='Dependent comment'))
        self.session.add(Comment(author_id=target.id,project_id=self.pid,body='Remove contribution'))
        kept_comment = Comment(author_id=keep.id,project_id=self.pid,body='Keep contribution')
        self.session.add(kept_comment)
        help_request = HelpRequest(project_id=self.pid,requester_id=keep.id,mentor_id=target.id,question='Keep question',answer='Remove answer',status='answered')
        self.session.add(help_request); self.session.flush()
        self.session.add(Endorsement(from_id=target.id,to_id=keep.id,skill='Python',help_request_id=help_request.id))
        challenge = Challenge(user_id=keep.id,prompt='Keep entry',ends_at=datetime.now(timezone.utc),judge_id=target.id,score=8,feedback='Remove review',post_id=post.id)
        self.session.add(challenge)
        thread = Thread()
        self.session.add(thread); self.session.flush()
        self.session.add_all([ThreadMember(thread_id=thread.id,user_id=person.id) for person in (keep,target)])
        status_message = Message(thread_id=thread.id,sender_id=keep.id,body='Follow request')
        self.session.add(status_message); self.session.flush()
        self.session.add(ConnectionRequest(low_id=min(keep.id,target.id),high_id=max(keep.id,target.id),sender_id=keep.id,recipient_id=target.id,thread_id=thread.id,message_id=status_message.id))
        self.session.add(Message(thread_id=thread.id,sender_id=target.id,body='Remove message'))
        kept_message = Message(thread_id=thread.id,sender_id=keep.id,body='Keep message')
        self.session.add(kept_message)
        self.session.add(ProfileSettingsRecord(user_id=keep.id,data={'pinned_project_ids':[self.pid,project.id],'pinned_post_id':post.id,'interests':['keep']}))
        self.session.add(ProfileSettingsRecord(user_id=target.id,data={}))
        self.session.commit()
        target_ids = {target.id,other_target.id}
        removed_project = project.id
        help_id, challenge_id, message_id, comment_id = help_request.id,challenge.id,kept_message.id,kept_comment.id
        preview = cleanup(self.session,target_ids,preview=True)
        self.assertIsNotNone(self.session.get(User,target.id))
        self.assertEqual(self.session.get(HelpRequest,help_id).answer,'Remove answer')
        self.assertEqual(self.session.get(Challenge,challenge_id).judge_id,target.id)
        self.assertEqual(self.session.get(ProfileSettingsRecord,keep.id).data['pinned_post_id'],post.id)
        result = cleanup(self.session,target_ids)
        self.assertEqual(preview,result)
        self.session.commit()
        self.assertEqual(result['deleted']['user'],2)
        self.assertIsNone(self.session.get(Project,removed_project))
        self.assertIsNotNone(self.session.get(Project,self.pid))
        self.assertIsNotNone(self.session.get(Message,message_id))
        self.assertIsNotNone(self.session.get(Comment,comment_id))
        self.assertEqual(self.session.get(HelpRequest,help_id).question,'Keep question')
        self.assertIsNone(self.session.get(HelpRequest,help_id).mentor_id)
        self.assertIsNone(self.session.get(HelpRequest,help_id).answer)
        kept_challenge = self.session.get(Challenge,challenge_id)
        self.assertIsNone(kept_challenge.judge_id)
        self.assertIsNone(kept_challenge.post_id)
        settings = self.session.get(ProfileSettingsRecord,keep.id).data
        self.assertEqual(settings,{'pinned_project_ids':[self.pid],'pinned_post_id':None,'interests':['keep']})
        self.assertEqual(self.session.exec(select(ConnectionRequest)).all(),[])

    def test_preview_rolls_back_all_changes(self):
        ids = {self.users[1].id,self.users[2].id}
        cleanup(self.session,ids)
        self.session.rollback()
        self.assertTrue(all(self.session.get(User,uid) for uid in ids))
        self.assertIsNotNone(self.session.get(Project,self.pid))
