import unittest
from datetime import datetime, timedelta, timezone
import test_messaging
from app.auth import current_user
from app.models import HelpRequest, LogEntry, Project, ProjectMember
from app.routers import home


class HomeSidebarTests(unittest.TestCase):
    def setUp(self):
        test_messaging.MessagingTests.setUp(self)
        self.app.include_router(home.router, prefix='/api')

    tearDown = test_messaging.MessagingTests.tearDown

    def project(self, title, **fields):
        project = Project(title=title, owner_id=fields.pop('owner_id', self.users[1].id), **fields)
        self.session.add(project); self.session.commit(); self.session.refresh(project)
        return project

    def sidebar(self):
        response = self.client.get('/api/home/sidebar')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_empty_state_and_authentication(self):
        result = self.sidebar()
        self.assertEqual(result, dict(my_projects=[], active_project_count=0, opportunities=[], help_requests=[]))
        del self.app.dependency_overrides[current_user]
        self.assertEqual(self.client.get('/api/home/sidebar').status_code, 401)

    def test_owned_and_joined_projects_exclude_archived_and_others(self):
        own = self.project('Own', owner_id=self.actor.id, looking_for=['Developer'])
        joined = self.project('Joined', looking_for=['Developer'])
        self.session.add(ProjectMember(project_id=joined.id, user_id=self.actor.id)); self.session.commit()
        self.project('Archived', owner_id=self.actor.id, status='archived')
        self.project('Other closed team')
        result = self.sidebar()
        self.assertEqual({item['project']['id'] for item in result['my_projects']}, {own.id, joined.id})
        self.assertEqual(result['active_project_count'], 2)
        self.assertEqual(result['opportunities'], [])

    def test_skill_matches_rank_first_with_real_match_reasons(self):
        self.actor.expertise_tags = ['Python']; self.session.add(self.actor); self.session.commit()
        self.project('No match', tags=['Design'], looking_for=['Designer'])
        match = self.project('Python team', tags=['Python'], looking_for=['Backend developer'])
        self.project('Archived match', tags=['Python'], looking_for=['Developer'], status='archived')
        result = self.sidebar()
        self.assertEqual(result['opportunities'][0]['project']['id'], match.id)
        self.assertEqual(result['opportunities'][0]['matched_skills'], ['Python'])
        self.assertEqual(result['opportunities'][1]['matched_skills'], [])

    def test_skill_graph_evidence_is_used_for_matching(self):
        self.project('SQL experience', owner_id=self.actor.id, tags=['SQL'])
        match = self.project('SQL opportunity', tags=['SQL'], looking_for=['Data engineer'])
        self.assertEqual(self.sidebar()['opportunities'][0]['project']['id'], match.id)
        self.assertEqual(self.sidebar()['opportunities'][0]['matched_skills'], ['SQL'])

    def test_latest_published_logs_and_personal_weekly_log_status(self):
        project = self.project('Team', owner_id=self.actor.id)
        now = datetime.now(timezone.utc)
        self.session.add_all([
            LogEntry(project_id=project.id, author_id=self.actor.id, title='My update', week_label='Now', created_at=now - timedelta(days=1)),
            LogEntry(project_id=project.id, author_id=self.users[1].id, title='Latest team update', week_label='Now', created_at=now),
            LogEntry(project_id=project.id, author_id=self.actor.id, title='Private draft', week_label='Now', created_at=now + timedelta(days=1), published=False),
        ]); self.session.commit()
        item = self.sidebar()['my_projects'][0]
        self.assertEqual(item['latest_log_title'], 'Latest team update')
        self.assertFalse(item['needs_log'])

    def test_card_lists_are_limited_and_total_count_is_accurate(self):
        for i in range(5):
            self.project(f'Mine {i}', owner_id=self.actor.id)
            self.project(f'Opportunity {i}', looking_for=['Developer'])
        result = self.sidebar()
        self.assertEqual(len(result['my_projects']), 3)
        self.assertEqual(result['active_project_count'], 5)
        self.assertEqual(len(result['opportunities']), 3)
        self.assertTrue(all(item['needs_log'] for item in result['my_projects']))

    def test_mentor_requests_exclude_own_archived_and_answered(self):
        active = self.project('Active')
        archived = self.project('Archived', status='archived')
        request = HelpRequest(project_id=active.id, requester_id=self.users[1].id, question='Python help', tags=['Python'], minutes=15)
        self.session.add_all([request,
            HelpRequest(project_id=active.id, requester_id=self.actor.id, question='My own question'),
            HelpRequest(project_id=archived.id, requester_id=self.users[1].id, question='Old question'),
            HelpRequest(project_id=active.id, requester_id=self.users[1].id, question='Done', status='answered'),
        ]); self.session.commit()
        self.assertEqual(self.sidebar()['help_requests'], [])
        self.actor.role = 'mentor'; self.actor.expertise_tags = ['Python']; self.session.add(self.actor); self.session.commit()
        result = self.sidebar()['help_requests']
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['request']['id'], request.id)
        self.assertEqual(result[0]['matched_skills'], ['Python'])
