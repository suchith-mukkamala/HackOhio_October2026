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

router = APIRouter(prefix="/admin", tags=["admin"])

ROLES = ("student", "mentor", "faculty")


class RedeemBody(SQLModel):
    code: str


class RoleBody(SQLModel):
    role: str


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


@router.get("/users", response_model=list[PublicUser])
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
