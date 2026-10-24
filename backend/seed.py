"""Reset the database and fill it with demo data.

    python seed.py

This is a starter set (Adi owns growing it to ~12 students, 5 mentors, 2 faculty,
6 projects). Point repo_full_name at real public repos you control so the GitHub
calls work during the demo.
"""

from sqlmodel import Session, SQLModel

from app.db import engine, init_db
from app.models import (
    Comment,
    Endorsement,
    HelpRequest,
    LogEntry,
    Post,
    Project,
    ProjectMember,
    User,
)


def run() -> None:
    SQLModel.metadata.drop_all(engine)
    init_db()

    with Session(engine) as s:
        users = {
            "maya": User(name="Maya Chen", role="student", major="Computer Science & Engineering", year="3rd year",
                         bio="Backend-curious, learning FastAPI by breaking it.", expertise_tags=["Python", "SQL"]),
            "jordan": User(name="Jordan Reyes", role="student", major="Mechanical Engineering", year="2nd year",
                           bio="Builds robots, wants to learn the software side.", expertise_tags=["CAD", "Arduino"]),
            "priya": User(name="Priya Natarajan", role="student", major="Design", year="4th year",
                          bio="UX researcher who prototypes in Figma.", expertise_tags=["UI Design", "UX Research", "Figma"]),
            "sam": User(name="Sam Okafor", role="mentor", company="Honda R&D", title="Software Engineer",
                        bio="Happy to give 15 minutes on backend and cloud.",
                        expertise_tags=["Python", "FastAPI", "AWS", "Docker", "System Design"]),
            "elena": User(name="Elena Park", role="mentor", company="99P Labs", title="Data Scientist",
                          bio="ML, data pipelines, and making charts honest.",
                          expertise_tags=["Machine Learning", "Data Analysis", "Python", "SQL"]),
            "drlee": User(name="Dr. Marcus Lee", role="faculty", company="Ohio State CSE", title="Senior Lecturer",
                          bio="Advises capstone teams.", expertise_tags=["System Design", "Testing", "Project Management"]),
        }
        s.add_all(users.values())
        s.commit()
        for u in users.values():
            s.refresh(u)

        transit = Project(
            owner_id=users["maya"].id, title="BuckeyeBus Live",
            description="Real-time campus bus arrivals with crowding estimates.",
            repo_full_name=None, tags=["Python", "FastAPI", "React", "SQL"],
            looking_for=["Frontend dev", "Data person"], start_date="2026-10-01", end_date="2026-11-12",
        )
        rover = Project(
            owner_id=users["jordan"].id, title="Mars Rover Arm",
            description="A 4-DOF arm for the rover club, controlled from a web dashboard.",
            tags=["Arduino", "C++", "CAD", "React"], looking_for=["Embedded dev"],
            start_date="2026-10-08", end_date="2026-11-19",
        )
        s.add_all([transit, rover])
        s.commit()
        s.refresh(transit)
        s.refresh(rover)

        s.add_all([
            ProjectMember(project_id=transit.id, user_id=users["maya"].id, role="owner"),
            ProjectMember(project_id=transit.id, user_id=users["priya"].id),
            ProjectMember(project_id=rover.id, user_id=users["jordan"].id, role="owner"),
        ])

        week1 = LogEntry(
            project_id=transit.id, author_id=users["maya"].id, week_label="Week of Oct 13",
            title="First live arrivals on the map",
            built=["FastAPI endpoint that polls the CABS feed every 30s",
                   "Postgres table for arrival history",
                   "React map with live bus markers"],
            learned=["Background tasks in FastAPI", "Indexing time-series rows"],
            stuck=["Arrival estimates drift when the feed lags"],
            skills=["Python", "FastAPI", "SQL", "React"],
        )
        s.add(week1)
        s.commit()
        s.refresh(week1)
        s.add(Post(author_id=users["maya"].id, project_id=transit.id, log_entry_id=week1.id,
                   body=week1.title, type="log"))

        s.add(HelpRequest(
            project_id=transit.id, requester_id=users["maya"].id,
            question="Our arrival estimates drift when the feed lags. Smooth in the backend or the client?",
            tags=["Python", "FastAPI", "System Design"], minutes=15,
        ))
        s.add(Endorsement(from_id=users["priya"].id, to_id=users["maya"].id, skill="React",
                          project_id=transit.id, note="Turned my Figma map into a working component in a day."))
        s.add(Comment(author_id=users["drlee"].id, project_id=transit.id,
                      body="Nice scope. Consider logging feed latency so you can show the drift."))
        s.commit()

    print("Seeded demo data.")


if __name__ == "__main__":
    run()
