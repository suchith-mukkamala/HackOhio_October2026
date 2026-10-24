"""Feed, posts, comments, search and DMs."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, field_validator
from sqlmodel import Session, SQLModel, select

from ..auth import current_user, optional_user
from ..services.profile_settings import preferences, may_contact, public_user
from ..db import get_session
from ..models import Comment, LogEntry, Message, Post, Project, PublicUser, Thread, ThreadMember, User

router = APIRouter(tags=["social"])


class PostIn(SQLModel):
    body: str
    project_id: Optional[int] = None
    type: str = "update"


class CommentIn(SQLModel):
    body: str
    post_id: Optional[int] = None
    project_id: Optional[int] = None


class MessageIn(SQLModel):
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body", mode="before")
    @classmethod
    def trim_body(cls, value):
        return value.strip() if isinstance(value, str) else value


class ThreadIn(SQLModel):
    user_ids: list[int] = Field(min_length=1, max_length=99)


# ---- Feed / posts / comments -----------------------------------------------


@router.get("/feed")
def feed(limit: int = 50, session: Session = Depends(get_session), viewer: User | None = Depends(optional_user)):
    posts = session.exec(select(Post).order_by(Post.created_at.desc()).limit(limit)).all()
    return post_items(session, posts, viewer)


def post_items(session: Session, posts, viewer: User | None = None):
    out = []
    for p in posts:
        author = session.get(User, p.author_id)
        if (not viewer or viewer.id != p.author_id) and not preferences(session, p.author_id).show_activity:
            continue
        linked_log = session.get(LogEntry, p.log_entry_id) if p.log_entry_id else None
        if linked_log and not linked_log.published:
            continue
        out.append(
            {
                "post": p,
                "author": public_user(session, author, viewer) if author else None,
                "project": session.get(Project, p.project_id) if p.project_id else None,
                "log": session.get(LogEntry, p.log_entry_id) if p.log_entry_id else None,
                "comments": session.exec(select(Comment).where(Comment.post_id == p.id)).all(),
            }
        )
    return out


@router.get("/users/{user_id}/posts")
def recent_user_posts(user_id: int, limit: int = Query(default=5, ge=1, le=20), session: Session = Depends(get_session), viewer: User | None = Depends(optional_user)):
    if not session.get(User, user_id):
        raise HTTPException(404, "User not found")
    posts = session.exec(
        select(Post)
        .outerjoin(LogEntry, Post.log_entry_id == LogEntry.id)
        .where(Post.author_id == user_id, (Post.log_entry_id == None) | (LogEntry.published == True))
        .order_by(Post.created_at.desc(), Post.id.desc())
        .limit(limit)
    ).all()
    prefs = preferences(session, user_id)
    if prefs.pinned_post_id and (prefs.show_activity or (viewer and viewer.id == user_id)):
        pinned = session.get(Post, prefs.pinned_post_id)
        if pinned and pinned.author_id == user_id:
            items = post_items(session, [pinned], viewer)
            if items:
                return (items + post_items(session, [p for p in posts if p.id != pinned.id], viewer))[:limit]
    return post_items(session, posts, viewer)


@router.post("/posts", response_model=Post)
def create_post(body: PostIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    post = Post(author_id=user.id, **body.model_dump())
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@router.post("/comments", response_model=Comment)
def create_comment(body: CommentIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if not body.post_id and not body.project_id:
        raise HTTPException(400, "A comment needs a post_id or a project_id")
    comment = Comment(author_id=user.id, **body.model_dump())
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


# ---- Search -----------------------------------------------------------------


@router.get("/search")
def search(q: str = "", type: str = "students", skill: str = "", session: Session = Depends(get_session)):
    needle = q.lower()
    if type == "projects":
        rows = session.exec(select(Project).where(Project.status == "active")).all()
        hits = [p for p in rows if needle in f"{p.title} {p.description} {' '.join(p.tags)}".lower()]
        if skill:
            hits = [p for p in hits if skill.lower() in (t.lower() for t in p.tags)]
        return hits

    role = "student" if type == "students" else None
    rows = session.exec(select(User)).all()
    hits = [
        u
        for u in rows
        if (u.role == role if role else u.role in ("mentor", "faculty"))
        and needle in f"{u.name} {u.major or ''} {u.company or ''} {u.bio or ''} {' '.join(u.expertise_tags)}".lower()
    ]
    if skill:
        hits = [u for u in hits if skill.lower() in (t.lower() for t in u.expertise_tags)]
    return [public_user(session, u) for u in hits]


# ---- DMs (clients poll; no websockets) --------------------------------------


@router.get("/threads")
def my_threads(user: User = Depends(current_user), session: Session = Depends(get_session)):
    thread_ids = session.exec(select(ThreadMember.thread_id).where(ThreadMember.user_id == user.id)).all()
    out = []
    for tid in thread_ids:
        others = session.exec(
            select(User).join(ThreadMember, ThreadMember.user_id == User.id).where(
                ThreadMember.thread_id == tid, User.id != user.id
            )
        ).all()
        last = session.exec(
            select(Message).where(Message.thread_id == tid).order_by(Message.created_at.desc(), Message.id.desc())
        ).first()
        out.append({"id": tid, "with": [public_user(session, o, user) for o in others], "last": last})
    return sorted(out, key=lambda t: t["last"].id if t["last"] else 0, reverse=True)


@router.post("/threads")
def start_thread(body: Optional[ThreadIn] = None, user_id: Optional[int] = None,
                 user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Reuse exact-member conversations without confusing groups with direct threads."""
    recipients = set(body.user_ids if body else ([user_id] if user_id is not None else []))
    recipients.discard(user.id)
    if not recipients:
        raise HTTPException(400, "Choose at least one other person")
    for recipient in recipients:
        if not session.get(User, recipient):
            raise HTTPException(404, "User not found")
    members = recipients | {user.id}
    mine = session.exec(select(ThreadMember.thread_id).where(ThreadMember.user_id == user.id)).all()
    for tid in mine:
        existing = set(session.exec(select(ThreadMember.user_id).where(ThreadMember.thread_id == tid)).all())
        if existing == members:
            return {"id": tid}
    for recipient in recipients:
        if not may_contact(session, user.id, recipient, len(members) > 2):
            raise HTTPException(403, "A recipient's messaging preferences do not allow this conversation")
    thread = Thread()
    session.add(thread)
    session.flush()
    session.add_all([ThreadMember(thread_id=thread.id, user_id=uid) for uid in members])
    session.commit()
    session.refresh(thread)
    return {"id": thread.id}


def require_member(session: Session, thread_id: int, user: User) -> None:
    if not session.get(ThreadMember, (thread_id, user.id)):
        raise HTTPException(403, "You're not in this conversation")


@router.get("/threads/{thread_id}/messages")
def messages(thread_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    require_member(session, thread_id, user)
    return session.exec(select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at, Message.id)).all()


@router.post("/threads/{thread_id}/messages", response_model=Message)
def send(thread_id: int, body: MessageIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    require_member(session, thread_id, user)
    msg = Message(thread_id=thread_id, sender_id=user.id, body=body.body)
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg
