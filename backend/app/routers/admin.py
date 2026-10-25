"""Admin-only routes.

Anyone signed in can become an admin by redeeming the secret ADMIN_CODE setting.
The code lives only in Vercel's environment variables (and backend/.env locally), never in
the repo or the frontend, so keep it out of Git.
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from ..auth import current_user
from ..config import settings
from ..db import get_session
from ..models import PublicUser, User
from ..models import Project
from ..services.user_cleanup import cleanup
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/admin", tags=["admin"])

ROLES = ("student", "mentor", "faculty")


class RedeemBody(SQLModel):
    code: str


class RoleBody(SQLModel):
    role: str


class AdminUser(PublicUser):
    username: str | None = None


class DeleteUserBody(SQLModel):
    confirmation: str


def require_admin(user: User = Depends(current_user)) -> User:
    """Use as a dependency on any route that only admins may call."""
    if not user.is_admin:
        raise HTTPException(403, "Admins only")
    return user


@router.post("/redeem", response_model=PublicUser)
def redeem(body: RedeemBody, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Type the secret code, become an admin."""
    if not settings.admin_code:
        raise HTTPException(404, "Admin access is not configured. Set ADMIN_CODE in the backend environment.")
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


def deletion_target(session: Session, user_id: int, actor: User):
    if user_id == actor.id:
        raise HTTPException(403, 'You cannot delete your own admin account')
    target = session.get(User, user_id)
    if not target:
        raise HTTPException(404, 'User not found')
    return target


@router.get('/users/{user_id}/deletion-preview')
def deletion_preview(user_id: int, actor: User = Depends(require_admin), session: Session = Depends(get_session)):
    target = deletion_target(session, user_id, actor)
    projects = session.exec(select(Project).where(Project.owner_id == user_id)).all()
    return dict(user=AdminUser.model_validate(target), owned_projects=[dict(id=project.id, title=project.title) for project in projects], **cleanup(session, {user_id}, preview=True))


@router.delete('/users/{user_id}')
def delete_user(user_id: int, body: DeleteUserBody, actor: User = Depends(require_admin), session: Session = Depends(get_session)):
    deletion_target(session, user_id, actor)
    if body.confirmation.strip() != f'DELETE {user_id}':
        raise HTTPException(400, f'Type DELETE {user_id} to confirm this account deletion')
    try:
        result = cleanup(session, {user_id})
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, 'The account could not be removed because related data changed. Refresh the preview and try again.')
    except Exception:
        session.rollback()
        raise
    return result
