"""Student orgs, timed build challenges, and the challenge's Ladder: Look around, Show up, Try something small, Join a project, Give back."""

import random
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, func, or_, select

from ..auth import current_user
from ..db import get_session
from ..models import Challenge, Club, ClubMember, Comment, Endorsement, HelpRequest, Post, ProjectMember, PublicUser, User

router = APIRouter(tags=["community"])


@router.get("/clubs")
def clubs(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Every org with its builder and project counts, and whether you're in it."""
    mine = set(session.exec(select(ClubMember.club_id).where(ClubMember.user_id == user.id)).all())
    out = []
    for c in session.exec(select(Club).order_by(Club.name)):
        member_ids = session.exec(select(ClubMember.user_id).where(ClubMember.club_id == c.id)).all()
        projects = session.exec(
            select(func.count(func.distinct(ProjectMember.project_id))).where(ProjectMember.user_id.in_(member_ids))
        ).one() if member_ids else 0
        out.append({**c.model_dump(), "members": len(member_ids), "projects": projects, "joined": c.id in mine})
    return out


@router.post("/clubs/{club_id}/join")
def toggle_join(club_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Join the org, or leave it if you're already in."""
    if not session.get(Club, club_id):
        raise HTTPException(404, "Org not found")
    row = session.get(ClubMember, (club_id, user.id))
    if row:
        session.delete(row)
    else:
        session.add(ClubMember(club_id=club_id, user_id=user.id))
    session.commit()
    return {"joined": row is None}


@router.get("/home/ladder")
def ladder(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Which rungs you've earned, from what you've actually done."""
    def count(stmt) -> int:
        return session.exec(stmt).one()

    my_posts = select(Post.id).where(Post.author_id == user.id)
    rungs = [
        ("Look around", True, "/explore"),
        ("Show up",
         count(select(func.count()).select_from(ClubMember).where(ClubMember.user_id == user.id))
         + count(select(func.count()).select_from(HelpRequest).where(HelpRequest.requester_id == user.id)) > 0,
         "#orgs"),
        ("Try something small",
         count(select(func.count()).select_from(Comment).where(
             Comment.author_id == user.id, or_(Comment.post_id.is_(None), Comment.post_id.not_in(my_posts)))) > 0  # feedback on someone else's work
         or count(select(func.count()).select_from(Challenge).where(Challenge.user_id == user.id, Challenge.submitted_at.is_not(None))) > 0,
         "/feed#feed"),
        ("Join a project",
         count(select(func.count()).select_from(ProjectMember).where(ProjectMember.user_id == user.id)) > 0,
         "/explore?category=projects"),
        ("Give back",
         count(select(func.count()).select_from(HelpRequest).where(HelpRequest.mentor_id == user.id)) > 0
         or count(select(func.count()).select_from(Endorsement).where(Endorsement.from_id == user.id)) > 0,
         "/explore"),
    ]
    return [{"name": n, "done": bool(d), "link": link} for n, d, link in rungs]


# ---- Timed build challenges ------------------------------------------------

# Random prompts are built from three parts, so there are hundreds of combinations
BUILD = ["a tool", "a bot", "a tiny game", "a dashboard", "a browser extension", "a map", "a matchmaker", "a tracker"]
FOR = ["first-year students", "commuters", "student org leaders", "TAs", "dining hall regulars",
       "people who study at Thompson Library", "intramural teams", "students looking for research"]
THAT = ["saves them 10 minutes a day", "uses only public campus data", "works in under 3 clicks",
        "helps them meet someone new", "reduces waste", "runs entirely offline", "uses AI in one honest way",
        "makes a boring task feel fun"]
HOURS = Literal[24, 48, 168, 336]  # 1 day, 2 days, 1 week, 2 weeks


class StartIn(BaseModel):
    hours: HOURS = 24


class SubmitIn(BaseModel):
    writeup: str = Field(min_length=1, max_length=2000)
    link: str = Field(default="", max_length=300)


class JudgeIn(BaseModel):
    score: int = Field(ge=1, le=10)
    feedback: str = Field(default="", max_length=1000)


def aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def challenge_out(c: Challenge, session: Session) -> dict:
    who = session.get(User, c.user_id)
    judge = session.get(User, c.judge_id) if c.judge_id else None
    return {**c.model_dump(), "user": PublicUser.model_validate(who) if who else None, "judge_name": judge.name if judge else None}


@router.post("/challenges")
def start_challenge(body: StartIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Sign up for a challenge: you get a random prompt and the clock starts."""
    open_one = session.exec(select(Challenge).where(Challenge.user_id == user.id, Challenge.submitted_at.is_(None))).all()
    if any(aware(c.ends_at) > datetime.now(timezone.utc) for c in open_one):
        raise HTTPException(400, "Finish or run out the clock on your current challenge first")
    prompt = f"Build {random.choice(BUILD)} for {random.choice(FOR)} that {random.choice(THAT)}."
    c = Challenge(user_id=user.id, prompt=prompt, hours=body.hours, ends_at=datetime.now(timezone.utc) + timedelta(hours=body.hours))
    session.add(c)
    session.commit()
    session.refresh(c)
    return challenge_out(c, session)


@router.get("/challenges")
def list_challenges(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Your challenges, and every submitted entry (newest first) for the gallery."""
    mine = session.exec(select(Challenge).where(Challenge.user_id == user.id).order_by(Challenge.id.desc())).all()
    entries = session.exec(select(Challenge).where(Challenge.submitted_at.is_not(None)).order_by(Challenge.submitted_at.desc())).all()
    return {"mine": [challenge_out(c, session) for c in mine], "entries": [challenge_out(c, session) for c in entries]}


@router.post("/challenges/{challenge_id}/submit")
def submit_challenge(challenge_id: int, body: SubmitIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Turn in your build before the clock runs out; it's shared to the feed for comments."""
    c = session.get(Challenge, challenge_id)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "Challenge not found")
    if c.submitted_at:
        raise HTTPException(400, "Already submitted")
    if aware(c.ends_at) < datetime.now(timezone.utc):
        raise HTTPException(400, "Time's up for this challenge. Start a new one!")
    text = "\n\n".join(filter(None, [f"Finished a {c.hours}-hour challenge: {c.prompt}", body.writeup, body.link]))
    post = Post(author_id=user.id, type="update", body=text)
    session.add(post)
    session.commit()
    session.refresh(post)
    c.writeup, c.link, c.submitted_at, c.post_id = body.writeup, body.link, datetime.now(timezone.utc), post.id
    session.add(c)
    session.commit()
    session.refresh(c)
    return challenge_out(c, session)


@router.post("/challenges/{challenge_id}/judge")
def judge_challenge(challenge_id: int, body: JudgeIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Mentors and faculty score a submitted entry out of 10, with feedback."""
    if user.role not in ("mentor", "faculty"):
        raise HTTPException(403, "Only mentors and faculty can judge")
    c = session.get(Challenge, challenge_id)
    if not c or not c.submitted_at:
        raise HTTPException(404, "Submitted entry not found")
    if c.user_id == user.id:
        raise HTTPException(403, "You can't judge your own entry")
    c.judge_id, c.score, c.feedback = user.id, body.score, body.feedback
    session.add(c)
    session.commit()
    session.refresh(c)
    return challenge_out(c, session)
