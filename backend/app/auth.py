"""Session cookie helpers. The cookie holds a signed JWT with the user id."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Response
from sqlmodel import Session

from .config import settings
from .db import get_session
from .models import User

COOKIE = "session"
ALGORITHM = "HS256"


def set_session_cookie(response: Response, user_id: int) -> None:
    token = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(days=7)},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        max_age=7 * 86400,
    )


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Not signed in")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "Session expired, sign in again")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(401, "User no longer exists")
    if user.is_banned:
        raise HTTPException(403, "This account has been suspended")
    return user


def optional_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    """Like current_user, but returns None instead of raising 401."""
    try:
        return current_user(request, session)
    except HTTPException:
        return None
