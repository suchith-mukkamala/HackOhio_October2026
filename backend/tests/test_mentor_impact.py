import unittest
import test_messaging
from app.auth import current_user
from app.models import HelpRequest, Project
from app.routers import help as help_routes


class MentorImpactTests(unittest.TestCase):
    def setUp(self):
        test_messaging.MessagingTests.setUp(self)
        self.app.include_router(help_routes.router,prefix='/api')
        self.actor.role='mentor';self.session.add(self.actor)
        self.project=Project(owner_id=self.users[1].id,title='Student project')
        self.session.add(self.project);self.session.commit()

    tearDown=test_messaging.MessagingTests.tearDown

    def request(self,student=None):
        request=HelpRequest(project_id=self.project.id,requester_id=(student or self.users[1]).id,question='How can I fix this?')
        self.session.add(request);self.session.commit();self.session.refresh(request)
        return request.id

    def count(self):
        result=self.client.get('/api/help/impact')
        self.assertEqual(result.status_code,200,result.text)
        return result.json()

    def test_repeat_help_for_same_student_increments_each_time(self):
        self.assertEqual(self.count()['students_helped'],0)
        for count in [1,2]:
            rid=self.request()
            self.assertEqual(self.client.post(f'/api/help/{rid}/answer',json={'answer':'Try this approach.'}).status_code,200)
            self.assertEqual(self.count()['students_helped'],count)
        self.assertEqual(self.count()['answered'],2)

    def test_marking_helpful_and_retrying_answer_do_not_double_count(self):
        mentor=self.actor;rid=self.request()
        self.client.post(f'/api/help/{rid}/answer',json={'answer':'An explanation.','endorse_skill':'Python'})
        self.assertEqual(self.count()['students_helped'],1)
        self.assertEqual(self.count()['skills_endorsed'],1)
        self.assertEqual(self.client.post(f'/api/help/{rid}/answer',json={'answer':'A retry'}).status_code,400)
        self.actor=self.users[1]
        self.assertEqual(self.client.post(f'/api/help/{rid}/helpful').status_code,200)
        self.actor=mentor
        self.assertEqual(self.count()['students_helped'],1)
        self.assertEqual(self.count()['marked_helpful'],1)

    def test_counts_exclude_open_requests_and_other_mentors(self):
        self.request()
        self.session.add(HelpRequest(project_id=self.project.id,requester_id=self.users[1].id,mentor_id=self.users[2].id,status='answered',answer='Another mentor',question='Question'))
        self.session.commit()
        self.assertEqual(self.count(),{'answered':0,'students_helped':0,'marked_helpful':0,'skills_endorsed':0})

    def test_faculty_supported_and_student_and_anonymous_rejected(self):
        self.actor.role='faculty';self.session.add(self.actor);self.session.commit()
        self.assertEqual(self.count()['students_helped'],0)
        self.actor=self.users[1]
        self.assertEqual(self.client.get('/api/help/impact').status_code,403)
        del self.app.dependency_overrides[current_user]
        self.assertEqual(self.client.get('/api/help/impact').status_code,401)
