from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from ..auth import current_user
from ..db import get_session
from ..models import Endorsement, Project, ProjectMember, PublicUser, User
from ..services import github
from ..services.skills import skill_graph

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
    return {
        "user": PublicUser.model_validate(user),
        "projects": projects,
        "endorsements": endorsements,
    }


@router.get("/users/{user_id}/skills")
def skills(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return skill_graph(session, user)


@router.get("/github/repos")
def my_repos(user: User = Depends(current_user)):
    if not user.github_token:
        raise HTTPException(400, "Connect GitHub first (sign in with GitHub)")
    return github.list_repos(user.github_token)
