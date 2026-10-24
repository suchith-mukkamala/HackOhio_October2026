"""Skill vocabulary and the evidence-weighted skill graph shown on profiles.

Score per skill = log(1 + code evidence) + 2 x peer endorsements
                  + 3 x mentor endorsements + 1 x helpful answers given.
Tier is the strongest kind of evidence: claimed < code < peer < mentor.

Hierarchy: every skill has a parent (another skill or a category), so the profile
can render a tree (Programming -> Python -> FastAPI). Parents "pulse" by the
strongest thing underneath them, so a category lights up when any child is strong.
"""

import math
from collections import defaultdict
from itertools import combinations

from sqlmodel import Session, select

from ..models import Endorsement, HelpRequest, LogEntry, Project, ProjectMember, User

# Fixed vocabulary so AI drafts, tags and endorsements all land on the same nodes.
SKILLS = [
    "Python", "TypeScript", "JavaScript", "React", "FastAPI", "Node.js", "SQL", "PostgreSQL",
    "AWS", "Docker", "Git", "REST APIs", "Auth / OAuth", "Testing", "CI/CD",
    "Machine Learning", "Data Analysis", "Computer Vision", "NLP / LLMs", "Prompt Engineering",
    "C", "C++", "Java", "Rust", "Go", "Embedded Systems", "Arduino", "ROS", "CAD",
    "UI Design", "UX Research", "Figma", "Technical Writing", "Project Management",
    "Public Speaking", "Debugging", "System Design", "Mobile Dev", "Swift", "Kotlin",
]

# Top-level branches. They are not skills: nobody claims or is endorsed for them.
CATEGORIES = ["Programming", "Web & Cloud", "Data & AI", "Hardware", "Design", "Professional"]

# child -> parent. A parent is either a category or another skill (children can have children).
PARENT = {
    # Programming
    "Python": "Programming", "JavaScript": "Programming", "C": "Programming", "C++": "Programming",
    "Java": "Programming", "Rust": "Programming", "Go": "Programming", "Mobile Dev": "Programming",
    "Debugging": "Programming", "Testing": "Programming",
    "FastAPI": "Python",
    "TypeScript": "JavaScript", "React": "JavaScript", "Node.js": "JavaScript",
    "Swift": "Mobile Dev", "Kotlin": "Mobile Dev",
    # Web & Cloud
    "REST APIs": "Web & Cloud", "Auth / OAuth": "Web & Cloud", "SQL": "Web & Cloud", "AWS": "Web & Cloud",
    "Docker": "Web & Cloud", "Git": "Web & Cloud", "CI/CD": "Web & Cloud", "System Design": "Web & Cloud",
    "PostgreSQL": "SQL",
    # Data & AI
    "Machine Learning": "Data & AI", "Data Analysis": "Data & AI",
    "Computer Vision": "Machine Learning", "NLP / LLMs": "Machine Learning",
    "Prompt Engineering": "NLP / LLMs",
    # Hardware
    "Embedded Systems": "Hardware", "CAD": "Hardware",
    "Arduino": "Embedded Systems", "ROS": "Embedded Systems",
    # Design
    "UI Design": "Design", "UX Research": "Design", "Figma": "UI Design",
    # Professional
    "Technical Writing": "Professional", "Project Management": "Professional", "Public Speaking": "Professional",
}

# GitHub language name -> vocabulary skill
LANGUAGE_TO_SKILL = {
    "Python": "Python", "TypeScript": "TypeScript", "JavaScript": "JavaScript", "C": "C",
    "C++": "C++", "Java": "Java", "Rust": "Rust", "Go": "Go", "Swift": "Swift",
    "Kotlin": "Kotlin", "Dockerfile": "Docker", "PLpgSQL": "SQL", "TSQL": "SQL",
}

TIER_RANK = {"claimed": 0, "code": 1, "peer": 2, "mentor": 3}

TOP_N = 12  # how many evidenced skills to show; their ancestors are added on top


def normalize(skill: str) -> str | None:
    lookup = {s.lower(): s for s in SKILLS}
    return lookup.get(skill.strip().lower())


def skill_vocabulary() -> dict:
    """Everything the onboarding picker needs to draw the full tree."""
    return {
        "categories": CATEGORIES,
        "skills": [{"skill": s, "parent": PARENT.get(s)} for s in SKILLS],
    }


def build_hierarchy(top: list[str], score: dict[str, float]) -> list[dict]:
    """Add ancestors of the shown skills and compute a 0..1 pulse for every node.

    pulse = the strongest score at or below the node, divided by the strongest score overall.
    Returns lightweight dicts: skill, parent, pulse, own (True if it has its own evidence).
    """
    keep = set(top)
    for s in top:
        p = PARENT.get(s)
        while p and p not in keep:
            keep.add(p)
            p = PARENT.get(p)

    children: dict[str, list[str]] = defaultdict(list)
    for c in keep:
        if PARENT.get(c) in keep:
            children[PARENT[c]].append(c)

    rolled: dict[str, float] = {}

    def roll(s: str) -> float:
        if s not in rolled:
            rolled[s] = max([score.get(s, 0.0)] + [roll(c) for c in children[s]])
        return rolled[s]

    peak = max((roll(s) for s in keep), default=0.0) or 1.0
    return [
        {"skill": s, "parent": PARENT.get(s), "pulse": round(roll(s) / peak, 2), "own": s in top}
        for s in keep
    ]


def skill_graph(session: Session, user: User) -> dict:
    score: dict[str, float] = defaultdict(float)
    tier: dict[str, str] = {}
    evidence: dict[str, list[dict]] = defaultdict(list)
    code_count: dict[str, int] = defaultdict(int)
    project_skills: list[set[str]] = []

    def bump(skill: str, new_tier: str) -> None:
        if TIER_RANK[new_tier] > TIER_RANK[tier.get(skill, "claimed")] or skill not in tier:
            tier[skill] = new_tier

    for s in user.expertise_tags:
        if (n := normalize(s)):
            bump(n, "claimed")
            evidence[n].append({"kind": "claimed", "label": "Listed on profile"})

    # Code evidence: skills in published logs the user wrote, and tags on their projects
    member_ids = session.exec(select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)).all()
    owned_ids = session.exec(select(Project.id).where(Project.owner_id == user.id)).all()
    for project in session.exec(select(Project).where(Project.id.in_(set(member_ids) | set(owned_ids)))):
        skills_here = {n for t in project.tags if (n := normalize(t))}
        for log in session.exec(
            select(LogEntry).where(LogEntry.project_id == project.id, LogEntry.author_id == user.id, LogEntry.published)
        ):
            for s in log.skills:
                if (n := normalize(s)):
                    skills_here.add(n)
                    code_count[n] += 1
                    evidence[n].append({"kind": "code", "label": f"{project.title}: {log.title}"})
        for n in skills_here:
            bump(n, "code")
        project_skills.append(skills_here)

    for n, count in code_count.items():
        score[n] += math.log1p(count * 5)

    for e in session.exec(select(Endorsement).where(Endorsement.to_id == user.id)):
        n = normalize(e.skill)
        if not n:
            continue
        giver = session.get(User, e.from_id)
        is_mentor = giver is not None and giver.role in ("mentor", "faculty")
        score[n] += 3 if is_mentor else 2
        bump(n, "mentor" if is_mentor else "peer")
        who = f"{giver.name} ({giver.company or giver.role})" if giver else "someone"
        evidence[n].append({"kind": "mentor" if is_mentor else "peer", "label": f"Endorsed by {who}: {e.note}"})

    for h in session.exec(select(HelpRequest).where(HelpRequest.mentor_id == user.id, HelpRequest.helpful)):
        for s in h.tags:
            if (n := normalize(s)):
                score[n] += 1
                bump(n, tier.get(n, "claimed"))
                evidence[n].append({"kind": "help_given", "label": f"Helped on: {h.question[:60]}"})

    for n in tier:
        score[n] = max(score[n], 0.5)  # claimed-only skills still get a small node

    edge_weight: dict[tuple[str, str], int] = defaultdict(int)
    for skills_here in project_skills:
        for a, b in combinations(sorted(skills_here), 2):
            edge_weight[(a, b)] += 1

    top = sorted(tier, key=lambda s: score[s], reverse=True)[:TOP_N]
    shown = build_hierarchy(top, score)
    nodes = []
    for h in shown:
        s = h["skill"]
        if h["own"]:
            nodes.append(
                {"skill": s, "parent": h["parent"], "score": round(score[s], 2), "pulse": h["pulse"],
                 "tier": tier[s], "evidence": evidence[s]}
            )
        else:
            # category, or a parent skill that only exists because a child is strong
            kind = "category" if s in CATEGORIES else "derived"
            nodes.append(
                {"skill": s, "parent": h["parent"], "score": 0, "pulse": h["pulse"], "tier": kind, "evidence": []}
            )

    return {
        "nodes": nodes,
        "edges": [
            {"a": a, "b": b, "weight": w} for (a, b), w in edge_weight.items() if a in top and b in top
        ],
    }
