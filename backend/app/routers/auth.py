import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..auth import COOKIE, set_session_cookie
from ..config import settings
from ..db import get_session
from ..models import PublicUser, User
from ..schemas import UserLogin, UserRegister
from ..services import github

router = APIRouter(prefix="/auth", tags=["auth"])
password_hasher = PasswordHash.recommended()
dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))


@router.post("/register", status_code=201)
def register(
    data: UserRegister,
    response: Response,
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(User).where(
            (User.username == data.username)
            | (User.email == str(data.email).lower())
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Username or email already exists",
        )

    user = User(
        username=data.username,
        name=data.name,
        email=str(data.email).lower(),
        password_hash=password_hasher.hash(data.password),
        role="student",
    )

    session.add(user)

    try:
        session.commit()
        session.refresh(user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Username or email already exists",
        )

    set_session_cookie(response, user.id)

    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }


@router.post("/login")
def login(
    data: UserLogin,
    response: Response,
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(User.username == data.username)
    ).first()

    # Verify a dummy hash for missing/passwordless accounts, too.
    stored_hash = user.password_hash if user and user.password_hash else dummy_hash
    try:
        valid = password_hasher.verify(data.password, stored_hash)
    except (UnknownHashError, ValueError):
        valid = False
    if user is None or not user.password_hash or not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    set_session_cookie(response, user.id)

    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
    }

@router.get("/github/login")
def github_login():
    if not settings.github_client_id:
        raise HTTPException(500, "GITHUB_CLIENT_ID is not set in backend/.env")
    state = secrets.token_urlsafe(16)
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "read:user repo",
            "state": state,
        }
    )
    resp = RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")
    resp.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax", secure=settings.secure_cookies)
    return resp


@router.get("/github/callback")
def github_callback(code: str, state: str, request: Request, session: Session = Depends(get_session)):
    expected_state = request.cookies.get("oauth_state")
    if not expected_state or not secrets.compare_digest(state.encode(), expected_state.encode()):
        raise HTTPException(400, "Sign-in expired. Start again from the home page.")
    try:
        token = github.exchange_code(
            settings.github_client_id, settings.github_client_secret, code, settings.github_redirect_uri
        )
        gh_user = github.get_viewer(token)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "GitHub sign-in could not be completed. Please try again.") from exc

    user = session.exec(select(User).where(User.github_username == gh_user["login"])).first()
    if not user:
        user = User(name=gh_user.get("name") or gh_user["login"], github_username=gh_user["login"])
    user.github_token = token
    user.avatar_url = gh_user.get("avatar_url")
    user.bio = user.bio or gh_user.get("bio")
    session.add(user)
    session.commit()
    session.refresh(user)

    resp = RedirectResponse(f"{settings.frontend_url}/feed")
    set_session_cookie(resp, user.id)
    resp.delete_cookie("oauth_state")
    return resp


@router.get("/demo/personas", response_model=list[PublicUser])
def demo_personas(session: Session = Depends(get_session)):
    if not settings.demo_mode:
        return []
    return session.exec(select(User).order_by(User.role, User.name)).all()


@router.post("/demo/{user_id}", status_code=204)
def demo_login(user_id: int, response: Response, session: Session = Depends(get_session)):
    if not settings.demo_mode:
        raise HTTPException(403, "Demo login is turned off")
    if not session.get(User, user_id):
        raise HTTPException(404, "No such persona")
    set_session_cookie(response, user_id)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(COOKIE)
