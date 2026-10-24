
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from pwdlib import PasswordHash

from .auth import set_session_cookie
from .db import get_session
from .models import User
from schemas import UserRegister, UserLogin

router = APIRouter()
password_hasher = PasswordHash.recommended()


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

    if user is None or not password_hasher.verify(
        data.password, user.password_hash
    ):
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
