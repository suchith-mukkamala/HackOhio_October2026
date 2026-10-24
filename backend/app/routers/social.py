"""Feed, posts, comments, search and DMs."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from ..auth import current_user
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
    body: str


# ---- Feed / posts / comments -----------------------------------------------


@router.get("/feed")
def feed(limit: int = 50, session: Session = Depends(get_session)):
    posts = session.exec(select(Post).order_by(Post.created_at.desc()).limit(limit)).all()
    out = []
    for p in posts:
        author = session.get(User, p.author_id)
        out.append(
            {
                "post": p,
                "author": PublicUser.model_validate(author) if author else None,
                "project": session.get(Project, p.project_id) if p.project_id else None,
                "log": session.get(LogEntry, p.log_entry_id) if p.log_entry_id else None,
                "comments": session.exec(select(Comment).where(Comment.post_id == p.id)).all(),
            }
        )
    return out


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
    return [PublicUser.model_validate(u) for u in hits]


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
            select(Message).where(Message.thread_id == tid).order_by(Message.created_at.desc())
        ).first()
        out.append({"id": tid, "with": [PublicUser.model_validate(o) for o in others], "last": last})
    return out


@router.post("/threads")
def start_thread(user_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Return the existing 1:1 thread with user_id, or create one."""
    if not session.get(User, user_id):
        raise HTTPException(404, "User not found")
    mine = set(session.exec(select(ThreadMember.thread_id).where(ThreadMember.user_id == user.id)).all())
    theirs = set(session.exec(select(ThreadMember.thread_id).where(ThreadMember.user_id == user_id)).all())
    if shared := mine & theirs:
        return {"id": min(shared)}
    thread = Thread()
    session.add(thread)
    session.commit()
    session.refresh(thread)
    session.add_all([ThreadMember(thread_id=thread.id, user_id=user.id), ThreadMember(thread_id=thread.id, user_id=user_id)])
    session.commit()
    return {"id": thread.id}


def require_member(session: Session, thread_id: int, user: User) -> None:
    if not session.get(ThreadMember, (thread_id, user.id)):
        raise HTTPException(403, "You're not in this conversation")


@router.get("/threads/{thread_id}/messages")
def messages(thread_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    require_member(session, thread_id, user)
    return session.exec(select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at)).all()


@router.post("/threads/{thread_id}/messages", response_model=Message)
def send(thread_id: int, body: MessageIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    require_member(session, thread_id, user)
    msg = Message(thread_id=thread_id, sender_id=user.id, body=body.body)
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg
