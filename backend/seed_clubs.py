"""Add sample student orgs (invented names) and put the team accounts in a few.

    python seed_clubs.py

Insert-only and safe to re-run: existing orgs and memberships are skipped.
"""

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Club, ClubMember, User

CLUBS = [
    ("Scarlet Robotics", "Engineering team", "Builds autonomous rovers for intercollegiate competitions.", "#ef4444"),
    ("Buckeye Rocketry Collective", "Engineering team", "High-power rockets, avionics and recovery systems.", "#f59e0b"),
    ("Hardware Hackers", "Maker space", "Weekly build nights: PCBs, 3D printing, embedded.", "#22c55e"),
    ("AI Reading Group", "Research", "One paper a week, then we try to reproduce it.", "#7c6cf6"),
    ("Design Collective", "Design", "UX critiques, Figma jams and portfolio reviews.", "#ec4899"),
    ("Buckeye Founders", "Entrepreneurship", "Student startups, from first idea to first user.", "#4f8cff"),
    ("Women Who Build", "Community", "Mentorship and build sprints for women in tech.", "#14b8a6"),
    ("Campus Data Lab", "Research", "Open data projects about life at Ohio State.", "#0ea5e9"),
]
TEAM = {"neel": ["AI Reading Group", "Buckeye Founders"], "rohan": ["Hardware Hackers", "Campus Data Lab"],
        "suchith": ["Scarlet Robotics", "Campus Data Lab"], "adi": ["Design Collective", "Buckeye Founders"]}


def run() -> None:
    init_db()
    with Session(engine) as s:
        have = {c.name for c in s.exec(select(Club))}
        s.add_all(Club(name=n, kind=k, blurb=b, color=col) for n, k, b, col in CLUBS if n not in have)
        s.commit()
        ids = {c.name: c.id for c in s.exec(select(Club))}
        for username, names in TEAM.items():
            user = s.exec(select(User).where(User.username == username)).first()
            for n in names:
                if user and not s.get(ClubMember, (ids[n], user.id)):
                    s.add(ClubMember(club_id=ids[n], user_id=user.id))
        s.commit()
        print(f"{len(ids)} orgs; team memberships added")


if __name__ == "__main__":
    run()
