"""Add the four team accounts and sample activity to the database in DATABASE_URL.

    python seed_team.py

Insert-only: never drops tables, and stops if the accounts already exist.
The shared password is read from password.txt at the repo root (git-ignored).
"""

from pathlib import Path

from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Comment, Endorsement, HelpRequest, LogEntry, Message, Post, Project, ProjectMember, Thread, ThreadMember, User

PASSWORD = (Path(__file__).resolve().parent.parent / "password.txt").read_text().strip()

TEAM = [
    dict(username="neel", name="Neel Mawalkar", major="Computer Science & Engineering", year="3rd year",
         bio="Builds AI tools that write the boring docs.", expertise_tags=["Python", "FastAPI", "NLP / LLMs"]),
    dict(username="rohan", name="Rohan Singh", major="Computer Science & Engineering", year="3rd year",
         bio="Auth, infra, and keeping the lights on in AWS.", expertise_tags=["AWS", "Docker", "Auth / OAuth"]),
    dict(username="suchith", name="Suchith Mukkamala", major="Electrical & Computer Engineering", year="2nd year",
         bio="Graphs, visualizations, and anything with nodes.", expertise_tags=["TypeScript", "React", "Data Analysis"]),
    dict(username="adi", name="Adi Duggal", major="Computer Science & Engineering", year="2nd year",
         bio="Search, messaging, and UI that just works.", expertise_tags=["React", "UI Design", "JavaScript"]),
]


def run() -> None:
    init_db()  # creates missing tables only
    with Session(engine) as s:
        if s.exec(select(User).where(User.username.in_([t["username"] for t in TEAM]))).first():
            print("Team accounts already exist; nothing changed.")
            return

        hasher = PasswordHash.recommended()
        u = {t["username"]: User(**t, role="student", email=f"{t['username']}@keystone.test", password_hash=hasher.hash(PASSWORD)) for t in TEAM}
        s.add_all(u.values())
        s.commit()
        for x in u.values():
            s.refresh(x)

        projects = {
            "keystone": Project(owner_id=u["neel"].id, title="Keystone", description="A portfolio AI can't fake: weekly logs, mentor help in minutes, skills backed by evidence.",
                                tags=["React", "FastAPI", "AWS", "NLP / LLMs"], looking_for=["Designer"], start_date="2026-10-24", end_date="2026-11-28"),
            "bus": Project(owner_id=u["adi"].id, title="BuckeyeBus Live", description="Real-time campus bus arrivals with crowding estimates.",
                           tags=["React", "Python", "SQL"], looking_for=["Data person"], start_date="2026-10-01", end_date="2026-11-12"),
            "rover": Project(owner_id=u["suchith"].id, title="Rover Arm Dashboard", description="Web dashboard to drive the rover club's 4-DOF arm.",
                             tags=["TypeScript", "React", "Embedded Systems"], looking_for=["Embedded dev"], start_date="2026-10-08", end_date="2026-11-19"),
        }
        s.add_all(projects.values())
        s.commit()
        for p in projects.values():
            s.refresh(p)
        P = {k: p.id for k, p in projects.items()}

        s.add_all([
            ProjectMember(project_id=P["keystone"], user_id=u[n].id, role="owner" if n == "neel" else "member") for n in u
        ] + [
            ProjectMember(project_id=P["bus"], user_id=u["adi"].id, role="owner"),
            ProjectMember(project_id=P["bus"], user_id=u["neel"].id),
            ProjectMember(project_id=P["rover"], user_id=u["suchith"].id, role="owner"),
            ProjectMember(project_id=P["rover"], user_id=u["rohan"].id),
        ])

        logs = [
            ("keystone", "neel", "Week of Oct 24", "Scaffold, feed and weekly logs are live",
             ["FastAPI backend with projects, logs and help requests", "Dark feed with weekly log cards", "Claude drafts logs from commits"],
             ["Structured output with Claude", "SQLModel relationships"], ["Keeping AI drafts honest, not polished"], ["Python", "FastAPI", "NLP / LLMs", "React"]),
            ("keystone", "rohan", "Week of Oct 24", "Accounts and the AWS database",
             ["Username/password register and login", "RDS Postgres on AWS"], ["Password hashing with argon2", "RDS networking"],
             ["Sharing DB credentials safely with the team"], ["AWS", "Auth / OAuth", "SQL"]),
            ("rover", "suchith", "Week of Oct 17", "Skill graph renders on profiles",
             ["Radial node graph component", "Arm joint angles streamed to the dashboard"], ["Force layouts", "WebSocket basics"],
             ["Graph gets crowded past 15 nodes"], ["TypeScript", "React", "Data Analysis"]),
            ("bus", "adi", "Week of Oct 17", "Search and messages",
             ["Explore search with filters", "Inbox with threads"], ["Debouncing input", "Accessible list patterns"], [], ["React", "UI Design"]),
        ]
        entries = []
        for proj, who, week, title, built, learned, stuck, skills in logs:
            e = LogEntry(project_id=P[proj], author_id=u[who].id, week_label=week, title=title, built=built, learned=learned, stuck=stuck, skills=skills, source="manual")
            s.add(e)
            entries.append((e, who, proj))
        s.commit()
        for e, who, proj in entries:
            s.refresh(e)
            s.add(Post(author_id=u[who].id, project_id=P[proj], log_entry_id=e.id, body=e.title, type="log"))
        s.add(Post(author_id=u["rohan"].id, body="Anyone have a good pattern for rotating RDS passwords during a hackathon? Asking for a friend."))
        s.commit()

        first_post = s.exec(select(Post).where(Post.log_entry_id == entries[0][0].id)).one()
        s.add_all([
            Comment(author_id=u["adi"].id, post_id=first_post.id, body="The log cards look great. Ship it."),
            Comment(author_id=u["suchith"].id, post_id=first_post.id, body="Can the skill tags link to my graph nodes?"),
            Comment(author_id=u["rohan"].id, project_id=P["keystone"], body="Login is wired to RDS now, try it out."),
            Endorsement(from_id=u["rohan"].id, to_id=u["neel"].id, skill="FastAPI", project_id=P["keystone"], note="Scaffolded the whole API in an afternoon."),
            Endorsement(from_id=u["neel"].id, to_id=u["rohan"].id, skill="AWS", project_id=P["keystone"], note="Got RDS running and shared it safely."),
            Endorsement(from_id=u["adi"].id, to_id=u["suchith"].id, skill="React", project_id=P["rover"], note="The skill graph component is slick."),
            Endorsement(from_id=u["suchith"].id, to_id=u["adi"].id, skill="UI Design", project_id=P["bus"], note="Search feels instant."),
            HelpRequest(project_id=P["rover"], requester_id=u["suchith"].id, question="Graph gets crowded past 15 nodes. Cluster, or cap the count?",
                        tags=["React", "Data Analysis"], minutes=15),
        ])
        t = Thread()
        s.add(t)
        s.commit()
        s.refresh(t)
        s.add_all([
            ThreadMember(thread_id=t.id, user_id=u["neel"].id),
            ThreadMember(thread_id=t.id, user_id=u["rohan"].id),
            Message(thread_id=t.id, sender_id=u["rohan"].id, body="DB is up. Check your .env."),
            Message(thread_id=t.id, sender_id=u["neel"].id, body="Connected. Adding the team accounts now."),
        ])
        s.commit()
    print("Added 4 team accounts with sample projects, logs, posts and endorsements.")


if __name__ == "__main__":
    run()
