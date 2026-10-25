"""Admin-only routes.

Anyone signed in can become an admin by redeeming the secret ADMIN_CODE setting.
The code lives only in Vercel's environment variables (and backend/.env locally), never in
the repo or the frontend, so keep it out of Git.

Moderation: ban or unban accounts, and delete posts and comments. A ban is enforced in
auth.current_user, so it takes effect on the very next request.
"""

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, col, select

from ..auth import current_user
from ..config import settings
from ..db import get_session
from ..models import Challenge, Comment, Post, PublicUser, User

router = APIRouter(prefix="/admin", tags=["admin"])

ROLES = ("student", "mentor", "faculty")


class RedeemBody(SQLModel):
    code: str


class RoleBody(SQLModel):
    role: str


class BanBody(SQLModel):
    delete_content: bool = False  # also remove every post and comment this person wrote


class AdminUser(PublicUser):
    """What admins see in the user list: the public profile plus moderation state."""

    username: Optional[str] = None
    is_banned: bool = False


def require_admin(user: User = Depends(current_user)) -> User:
    """Use as a dependency on any route that only admins may call."""
    if not user.is_admin:
        raise HTTPException(403, "Admins only")
    return user


@router.post("/redeem", response_model=PublicUser)
def redeem(body: RedeemBody, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Type the secret code, become an admin."""
    if not settings.admin_code:
        raise HTTPException(404, "Admin access is turned off")
    # compare_digest takes the same time however many characters match
    if not secrets.compare_digest(body.code.strip().encode(), settings.admin_code.encode()):
        raise HTTPException(403, "That code is not valid")
    user.is_admin = True
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("/users", response_model=list[AdminUser])
def all_users(_: User = Depends(require_admin), session: Session = Depends(get_session)):
    return session.exec(select(User).order_by(User.id)).all()


@router.put("/users/{user_id}/role", response_model=PublicUser)
def set_role(
    user_id: int,
    body: RoleBody,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """Switch anyone between student, mentor and faculty (handy for demoing both sides)."""
    if body.role not in ROLES:
        raise HTTPException(400, f"Role must be one of: {', '.join(ROLES)}")
    target = session.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    target.role = body.role
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


# ---- Moderation ------------------------------------------------------------


def remove_posts(session: Session, post_ids: list[int]) -> None:
    """Delete posts and everything pointing at them (comments, challenge links). Caller commits."""
    if not post_ids:
        return
    for comment in session.exec(select(Comment).where(col(Comment.post_id).in_(post_ids))).all():
        session.delete(comment)
    for challenge in session.exec(select(Challenge).where(col(Challenge.post_id).in_(post_ids))).all():
        challenge.post_id = None  # keep the challenge, just unlink the feed post
        session.add(challenge)
    session.flush()
    for post in session.exec(select(Post).where(col(Post.id).in_(post_ids))).all():
        session.delete(post)
    session.flush()


@router.post("/users/{user_id}/ban", response_model=AdminUser)
def ban_user(
    user_id: int,
    body: Optional[BanBody] = None,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """Suspend an account. Their data stays (so the username and email stay taken); they just can't act or sign in."""
    target = session.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == admin.id:
        raise HTTPException(400, "You can't ban yourself")
    if target.is_admin:
        raise HTTPException(400, "Admins can't be banned")
    target.is_banned = True
    session.add(target)
    if body and body.delete_content:
        for comment in session.exec(select(Comment).where(Comment.author_id == target.id)).all():
            session.delete(comment)
        session.flush()
        remove_posts(session, list(session.exec(select(Post.id).where(Post.author_id == target.id)).all()))
    session.commit()
    session.refresh(target)
    return target


@router.post("/users/{user_id}/unban", response_model=AdminUser)
def unban_user(user_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    target = session.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    target.is_banned = False
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    """Remove a post and its comments from the feed."""
    if not session.get(Post, post_id):
        raise HTTPException(404, "Post not found")
    remove_posts(session, [post_id])
    session.commit()


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    comment = session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(404, "Comment not found")
    session.delete(comment)
    session.commit()
