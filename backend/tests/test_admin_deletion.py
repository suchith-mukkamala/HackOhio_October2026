"""Admin deletion authorization, read-only previews, atomic cleanup and identity checks."""
import unittest
from unittest.mock import patch
import test_projects
from app.auth import current_user
from app.models import User, Project, ProjectMember, Post, Comment
from app.routers import admin


class AdminDeletionTests(unittest.TestCase):
    def setUp(self):
        test_projects.ProjectPermissionTests.setUp(self)
        self.app.include_router(admin.router,prefix='/api')
        self.actor.is_admin=True
        self.session.add(self.actor)
        self.session.commit()
        self.target_id=self.users[1].id
        self.delete_path=f'/api/admin/users/{self.target_id}'

    tearDown=test_projects.ProjectPermissionTests.tearDown

    def delete(self,confirmation=None):
        return self.client.request('DELETE',self.delete_path,json={'confirmation':confirmation or f'DELETE {self.target_id}'})

    def test_preview_and_delete_match_and_preserve_unrelated_work(self):
        owned=Project(owner_id=self.target_id,title='Owned by target')
        self.session.add(owned);self.session.flush()
        self.session.add(ProjectMember(project_id=owned.id,user_id=self.users[3].id))
        self.session.add(Post(author_id=self.target_id,project_id=self.pid,body='Target contribution'))
        self.session.add(Comment(author_id=self.users[3].id,project_id=owned.id,body='Dependent on owned project'))
        keep=Comment(author_id=self.users[3].id,project_id=self.pid,body='Keep unrelated comment')
        self.session.add(keep);self.session.commit()
        owned_id,keep_id=owned.id,keep.id
        response=self.client.get(self.delete_path+'/deletion-preview')
        self.assertEqual(response.status_code,200,response.text)
        preview=response.json()
        self.assertEqual(preview['owned_projects'],[{'id':owned_id,'title':'Owned by target'}])
        self.assertIsNotNone(self.session.get(User,self.target_id))
        self.assertIsNotNone(self.session.get(Project,owned_id))
        result=self.delete()
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['deleted'],preview['deleted'])
        self.assertIsNone(self.session.get(User,self.target_id))
        self.assertIsNone(self.session.get(Project,owned_id))
        self.assertIsNotNone(self.session.get(Project,self.pid))
        self.assertIsNotNone(self.session.get(Comment,keep_id))
        self.assertIsNotNone(self.session.get(User,self.users[3].id))

    def test_confirmation_is_bound_to_exact_user_id(self):
        self.assertEqual(self.delete('DELETE 999999').status_code,400)
        self.assertIsNotNone(self.session.get(User,self.target_id))

    def test_self_deletion_and_missing_accounts_rejected(self):
        own=f'/api/admin/users/{self.actor.id}'
        self.assertEqual(self.client.get(own+'/deletion-preview').status_code,403)
        self.assertEqual(self.client.request('DELETE',own,json={'confirmation':f'DELETE {self.actor.id}'}).status_code,403)
        self.assertEqual(self.client.get('/api/admin/users/999999/deletion-preview').status_code,404)

    def test_non_admin_and_signed_out_users_cannot_preview_or_delete(self):
        self.actor=self.users[2]
        self.assertEqual(self.client.get(self.delete_path+'/deletion-preview').status_code,403)
        self.assertEqual(self.delete().status_code,403)
        del self.app.dependency_overrides[current_user]
        self.assertEqual(self.client.get(self.delete_path+'/deletion-preview').status_code,401)
        self.assertEqual(self.delete().status_code,401)

    def test_failure_rolls_back_deletion(self):
        def failing_cleanup(session,ids):
            session.delete(session.get(User,self.target_id))
            session.flush()
            raise RuntimeError('Simulated failure')
        with patch.object(admin,'cleanup',side_effect=failing_cleanup):
            with self.assertRaises(RuntimeError):self.delete()
        self.assertIsNotNone(self.session.get(User,self.target_id))

    def test_admin_list_identifies_users_without_secrets(self):
        target=self.session.get(User,self.target_id)
        target.username='target-account'
        target.password_hash='private'
        target.github_token='private'
        self.session.add(target);self.session.commit()
        response=self.client.get('/api/admin/users').json()
        self.assertEqual(next(row for row in response if row['id']==self.target_id)['username'],'target-account')
        self.assertNotIn('password_hash',str(response))
        self.assertNotIn('github_token',str(response))
