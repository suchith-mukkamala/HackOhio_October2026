import base64
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel import Field, Session, SQLModel, select  # CHANGED: added Field

from ..auth import current_user
from ..db import get_session
from ..models import Endorsement, Experience, Project, ProjectMember, PublicUser, User
from ..services import ai, github
from ..services.skills import normalize, skill_graph, skill_vocabulary

router = APIRouter(tags=["users"])

BIO_MAX_LENGTH = 500  # NEW: keep in sync with BIO_MAX_LENGTH in frontend/src/pages/Profile.tsx


class MeUpdate(SQLModel):
    """Fields a user may edit on their own profile. role and github_token are deliberately absent."""

    bio: Optional[str] = Field(default=None, max_length=BIO_MAX_LENGTH)  # CHANGED: length limit
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
    changes = body.model_dump(exclude_unset=True)

    if "expertise_tags" in changes:
        raw_tags = changes.pop("expertise_tags")
        if raw_tags is not None:  # an explicit null means "leave it alone"
            tags: list[str] = []
            unknown: list[str] = []
            for raw in raw_tags:
                skill = normalize(raw)
                if not skill:
                    unknown.append(raw)
                elif skill not in tags:
                    tags.append(skill)
            if unknown:
                raise HTTPException(400, f"Unknown skills: {', '.join(unknown)}")
            changes["expertise_tags"] = tags

    # NEW: trim whitespace; a blank bio clears it
    if "bio" in changes:
        bio = (changes["bio"] or "").strip()
        changes["bio"] = bio or None

    for field, value in changes.items():
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
    """Read a PDF resume: replace work/education history (with skills for the graph), fill empty profile fields."""
    data = file.file.read()
    if not data.startswith(b"%PDF") or len(data) > 10_000_000:
        raise HTTPException(400, "Upload a PDF under 10 MB")
    try:
        parsed = ai.parse_resume(base64.b64encode(data).decode())
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    for old in session.exec(select(Experience).where(Experience.user_id == user.id)):
        session.delete(old)
    session.add_all(Experience(user_id=user.id, **e.model_dump()) for e in parsed.entries)
    filled = []  # never overwrite what the user wrote themselves
    if parsed.bio and not user.bio:
        user.bio, filled = parsed.bio, filled + ["bio"]
    if parsed.major and not user.major and user.role == "student":
        user.major, filled = parsed.major, filled + ["major"]
    session.add(user)
    session.commit()
    skills = sorted({s for e in parsed.entries for s in e.skills})
    return {"entries": len(parsed.entries), "skills": skills, "filled": filled}


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
