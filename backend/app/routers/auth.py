import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..auth import COOKIE, optional_user, set_session_cookie
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


def _state_ok(state: str, request: Request) -> bool:
    expected = request.cookies.get("oauth_state")
    return bool(expected) and secrets.compare_digest(state.encode(), expected.encode())


# ---- GitHub ----------------------------------------------------------------


@router.get("/github/login")
def github_login():
    if not settings.github_client_id:
        raise HTTPException(500, "GITHUB_CLIENT_ID is not set in backend/.env")
    state = secrets.token_urlsafe(16)
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            # public_repo reads public repos' commits and READMEs. "repo" would grant
            # full access to every private repo, which we don't need.
            "scope": "read:user public_repo",
            "state": state,
        }
    )
    resp = RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")
    resp.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax", secure=settings.secure_cookies)
    return resp


@router.get("/github/callback")
def github_callback(
    code: str,
    state: str,
    request: Request,
    session: Session = Depends(get_session),
    current: User | None = Depends(optional_user),
):
    if not _state_ok(state, request):
        raise HTTPException(400, "Sign-in expired. Start again from the home page.")
    try:
        token = github.exchange_code(
            settings.github_client_id, settings.github_client_secret, code, settings.github_redirect_uri
        )
        gh_user = github.get_viewer(token)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "GitHub sign-in could not be completed. Please try again.") from exc

    login_name = gh_user["login"]
    with_this_github = session.exec(select(User).where(User.github_username == login_name)).first()

    if current:
        # Already signed in: link GitHub to this account instead of making a second one.
        if with_this_github and with_this_github.id != current.id:
            raise HTTPException(409, "That GitHub account is already linked to another user.")
        user = current
    else:
        user = with_this_github

    if not user:
        username = login_name
        if session.exec(select(User).where(User.username == username)).first():
            username = f"{login_name}-gh"
        user = User(username=username, name=gh_user.get("name") or login_name)

    user.github_username = login_name
    user.github_token = token
    user.avatar_url = gh_user.get("avatar_url") or user.avatar_url
    user.bio = user.bio or gh_user.get("bio")
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Could not create your account. Try again.")
    session.refresh(user)

    resp = RedirectResponse(f"{settings.frontend_url}/feed")
    set_session_cookie(resp, user.id)
    resp.delete_cookie("oauth_state")
    return resp


# ---- Google ----------------------------------------------------------------


@router.get("/google/login")
def google_login():
    if not settings.google_client_id:
        raise HTTPException(500, "GOOGLE_CLIENT_ID is not set in backend/.env")
    state = secrets.token_urlsafe(16)
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
    )
    resp = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")
    resp.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax", secure=settings.secure_cookies)
    return resp


@router.get("/google/callback")
def google_callback(
    code: str,
    state: str,
    request: Request,
    session: Session = Depends(get_session),
    current: User | None = Depends(optional_user),
):
    """Signs in the account with this Google email, or creates a student account for it."""
    if not _state_ok(state, request):
        raise HTTPException(400, "Sign-in expired. Start again from the home page.")
    try:
        token = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        ).raise_for_status().json()["access_token"]
        info = httpx.get(
            "https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {token}"}, timeout=15
        ).raise_for_status().json()
    except (httpx.HTTPError, KeyError) as exc:
        raise HTTPException(502, "Google sign-in could not be completed. Please try again.") from exc
    if not info.get("email_verified"):
        raise HTTPException(400, "Your Google email isn't verified.")

    email = info["email"].lower()
    user = session.exec(select(User).where(User.email == email)).first()

    if user and user.password_hash and not (current and current.id == user.id):
        # Someone could have registered a password account with this email without proving
        # they own it. Don't hand that account to whoever holds the Google address.
        raise HTTPException(409, "An account with this email already exists. Sign in with your password.")

    if not user:
        user = User(name=info.get("name") or email, email=email, avatar_url=info.get("picture"))
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "Could not create your account. Try again.")
        session.refresh(user)

    resp = RedirectResponse(f"{settings.frontend_url}/feed")
    set_session_cookie(resp, user.id)
    resp.delete_cookie("oauth_state")
    return resp


# ---- Demo ------------------------------------------------------------------


def _is_demo_persona(user: User) -> bool:
    """Seeded personas only: no password and no GitHub token. Real accounts can't be demo-logged-into."""
    return not user.password_hash and not user.github_token


@router.get("/demo/personas", response_model=list[PublicUser])
def demo_personas(session: Session = Depends(get_session)):
    if not settings.demo_mode:
        return []
    users = session.exec(select(User).order_by(User.role, User.name)).all()
    return [u for u in users if _is_demo_persona(u)]


@router.post("/demo/{user_id}", status_code=204)
def demo_login(user_id: int, response: Response, session: Session = Depends(get_session)):
    if not settings.demo_mode:
        raise HTTPException(403, "Demo login is turned off")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "No such persona")
    if not _is_demo_persona(user):
        raise HTTPException(403, "That account is not a demo persona")
    set_session_cookie(response, user_id)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(COOKIE)
