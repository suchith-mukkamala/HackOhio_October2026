"""Student orgs, and the challenge's Ladder: Look around, Show up, Try something small, Join a project, Give back."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, or_, select

from ..auth import current_user
from ..db import get_session
from ..models import Club, ClubMember, Comment, Endorsement, HelpRequest, Post, ProjectMember, User

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
             Comment.author_id == user.id, or_(Comment.post_id.is_(None), Comment.post_id.not_in(my_posts)))) > 0,  # feedback on someone else's work
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
