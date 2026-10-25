"""Fill the home feed with realistic sample activity: people, photo/video posts, mentor comments, judged challenges.

    python seed_home.py

Insert-only and safe to re-run (stops if the sample people already exist).
Sample people have usernames starting with "sample_" and no password, so nobody can sign in as them.
"""

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Challenge, Club, ClubMember, Comment, Post, User

PEOPLE = [
    dict(username="sample_marcus", name="Marcus Bell", role="mentor", title="Senior Software Engineer", company="Honda R&D",
         bio="Embedded + cloud. Happy to review your architecture in 15 minutes.", expertise_tags=["Python", "AWS", "Embedded Systems"]),
    dict(username="sample_elena", name="Elena Park", role="mentor", title="Data Scientist", company="99P Labs",
         bio="Mobility data, honest charts, and asking 'what would change your mind?'", expertise_tags=["Data Analysis", "Machine Learning", "SQL"]),
    dict(username="sample_raman", name="Dr. Priya Raman", role="faculty", title="Associate Professor", company="Ohio State CSE",
         bio="Advises capstone teams. Ask me about scoping.", expertise_tags=["System Design", "Testing"]),
    dict(username="sample_jordan", name="Jordan Reyes", role="student", major="Mechanical Engineering", year="2nd year",
         bio="Rover club. Learning the software side.", expertise_tags=["CAD", "Arduino"]),
    dict(username="sample_aisha", name="Aisha Okafor", role="student", major="Design", year="3rd year",
         bio="UX for things people actually use on campus.", expertise_tags=["UI Design", "Figma", "UX Research"]),
    dict(username="sample_liam", name="Liam Chen", role="student", major="Computer Science & Engineering", year="1st year",
         bio="First hackathon season. Saying yes to everything.", expertise_tags=["Python", "JavaScript"]),
]

IMG = "https://picsum.photos/seed/{}/1200/675"
VIDEO = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"

# (author, hours ago, body, media url, media kind, [(commenter, comment)])
POSTS = [
    ("sample_jordan", 2, "Rover arm picked up its first sample cup today. 4-DOF, all 3D printed. Next week: closing the loop on the wrist joint.",
     IMG.format("rover-arm"), "image", [("sample_marcus", "Nice work. Log the joint angles so you can tune the wrist with real data."),
                                        ("sample_liam", "This is so cool, is the club looking for new people?")]),
    ("sample_aisha", 5, "Ran a 6-person usability test on the bus arrival screen. Biggest finding: nobody noticed the 'delayed' color, so we're switching to a text label.",
     IMG.format("usability-test"), "image", [("sample_raman", "Exactly the kind of evidence that makes a design decision easy. Keep the notes."),
                                             ("sample_elena", "Did you time how long it took people to find their bus? Great before/after metric.")]),
    ("sample_liam", 9, "Finished my first 24-hour challenge: a study-room finder for Thompson Library. Rough, but it works on my phone.",
     IMG.format("library-study"), "image", [("sample_elena", "Shipping something in 24 hours is the hard part. Proud of you."),]),
    ("sample_marcus", 14, "Office hours this Thursday: bring an architecture diagram and a question. I'll spend 15 minutes on each team.",
     None, None, [("sample_jordan", "Signing up for the rover dashboard!")]),
    ("sample_aisha", 20, "Short clip of the new onboarding animation. Feedback welcome, especially on timing.",
     VIDEO, "video", [("sample_raman", "Smooth. Try shaving 200 ms off the first step.")]),
    ("sample_elena", 30, "Reading list for anyone starting a data project this month: start with the question, then the dataset, then the model. Never the other way around.",
     IMG.format("data-notes"), "image", []),
]

CHALLENGES = [  # (student, prompt, writeup, judge, score, feedback)
    ("sample_liam", "Build a tool for people who study at Thompson Library that saves them 10 minutes a day.",
     "A study-room finder that reads the public room calendar and shows what's free in the next hour.", "sample_elena", 8,
     "Clear problem, working demo. Add a 'free for 2+ hours' filter and you'd use it daily."),
    ("sample_aisha", "Build a map for first-year students that works in under 3 clicks.",
     "A 'where's my class' map: pick a course, see the building and the fastest walking route.", "sample_raman", 9,
     "Tight scope and great usability testing. This is how to run a 48-hour build."),
]


def run() -> None:
    init_db()
    now = datetime.now(timezone.utc)
    with Session(engine) as s:
        if s.exec(select(User).where(User.username == "sample_marcus")).first():
            print("Sample data already there; nothing changed.")
            return
        people = {p["username"]: User(**p, email=f"{p['username']}@example.com") for p in PEOPLE}
        s.add_all(people.values())
        s.commit()
        u = {k: s.exec(select(User).where(User.username == k)).one().id for k in people}

        for author, hours, body, url, kind, comments in POSTS:
            post = Post(author_id=u[author], body=body, media_url=url, media_kind=kind, created_at=now - timedelta(hours=hours))
            s.add(post)
            s.commit()
            s.refresh(post)
            s.add_all(Comment(author_id=u[who], post_id=post.id, body=text, created_at=now - timedelta(hours=hours - 1))
                      for who, text in comments)
        s.commit()

        for student, prompt, writeup, judge, score, feedback in CHALLENGES:
            done = now - timedelta(hours=8)
            s.add(Challenge(user_id=u[student], prompt=prompt, hours=24, started_at=done - timedelta(hours=20),
                            ends_at=done + timedelta(hours=4), writeup=writeup, submitted_at=done,
                            judge_id=u[judge], score=score, feedback=feedback))

        clubs = {c.name: c.id for c in s.exec(select(Club))}
        for student, org in [("sample_jordan", "Scarlet Robotics"), ("sample_aisha", "Design Collective"),
                             ("sample_liam", "Hardware Hackers"), ("sample_liam", "AI Reading Group")]:
            if org in clubs:
                s.add(ClubMember(club_id=clubs[org], user_id=u[student]))
        s.commit()
    print(f"Added {len(PEOPLE)} sample people, {len(POSTS)} posts, {sum(len(p[5]) for p in POSTS)} comments, {len(CHALLENGES)} judged challenges.")


if __name__ == "__main__":
    run()
