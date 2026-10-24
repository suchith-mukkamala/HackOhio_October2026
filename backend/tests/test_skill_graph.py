import unittest
import test_messaging
from app.models import Experience
from app.services.skills import SKILLS, skill_graph


class SkillGraphTests(unittest.TestCase):
    setUp = test_messaging.MessagingTests.setUp
    tearDown = test_messaging.MessagingTests.tearDown

    def test_all_claimed_skills_are_present_beyond_old_cap(self):
        user = self.users[0]
        user.expertise_tags = list(SKILLS)
        self.session.add(user); self.session.commit()
        graph = skill_graph(self.session, user)
        names = {node['skill'] for node in graph['nodes']}
        self.assertTrue(set(SKILLS) <= names)
        self.assertEqual(len(names), len(graph['nodes']))
        for node in graph['nodes']:
            if node['parent']:
                self.assertIn(node['parent'], names)
        self.assertEqual(graph, skill_graph(self.session, user))

    def test_resume_skills_are_not_displaced_by_claimed_skills(self):
        user = self.users[0]
        user.expertise_tags = SKILLS[:20]
        self.session.add(user)
        self.session.add(Experience(user_id=user.id, kind='work', title='Engineer', org='Team', skills=SKILLS[20:]))
        self.session.commit()
        graph = skill_graph(self.session, user)
        self.assertTrue(set(SKILLS) <= {node['skill'] for node in graph['nodes']})
