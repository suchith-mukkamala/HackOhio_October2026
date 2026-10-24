import base64
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel import Session, SQLModel, select

from ..auth import current_user
from ..db import get_session
from ..models import Endorsement, Experience, Project, ProjectMember, PublicUser, User
from ..services import ai, github
from ..services.skills import skill_graph, skill_vocabulary

router = APIRouter(tags=["users"])


class MeUpdate(SQLModel):
    """Fields a user may edit on their own profile. role and github_token are deliberately absent."""

    bio: Optional[str] = None
    major: Optional[str] = None
    year: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    expertise_tags: Optional[list[str]] = None


@router.get("/me", response_model=PublicUser)
def me(user: User = Depends(current_user)):
    return user


@router.put("/me", response_model=PublicUser)
def update_me(body: MeUpdate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("/users/{user_id}")
def profile(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    member_ids = session.exec(select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)).all()
    projects = session.exec(
        select(Project).where((Project.owner_id == user_id) | (Project.id.in_(member_ids)))
    ).all()
    endorsements = session.exec(select(Endorsement).where(Endorsement.to_id == user_id)).all()
    experience = session.exec(select(Experience).where(Experience.user_id == user_id).order_by(Experience.id)).all()
    return {
        "user": PublicUser.model_validate(user),
        "projects": projects,
        "endorsements": endorsements,
        "experience": experience,
    }


@router.post("/me/resume")
def upload_resume(file: UploadFile, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Read a PDF resume and replace the user's work and education history with what's in it."""
    data = file.file.read()
    if not data.startswith(b"%PDF") or len(data) > 10_000_000:
        raise HTTPException(400, "Upload a PDF under 10 MB")
    try:
        entries = ai.parse_resume(base64.b64encode(data).decode())
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    for old in session.exec(select(Experience).where(Experience.user_id == user.id)):
        session.delete(old)
    session.add_all(Experience(user_id=user.id, **e.model_dump()) for e in entries)
    session.commit()
    return [e.model_dump() for e in entries]


@router.get("/users/{user_id}/skills")
def skills(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return skill_graph(session, user)


@router.get("/skills/vocabulary")
def vocabulary():
    """The fixed skill tree, for the onboarding picker."""
    return skill_vocabulary()


@router.get("/github/repos")
def my_repos(user: User = Depends(current_user)):
    if not user.github_token:
        raise HTTPException(400, "Connect GitHub first (sign in with GitHub)")
    return github.list_repos(user.github_token)
