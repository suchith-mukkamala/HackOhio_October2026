"""Owner-only settings, experience management, and account controls."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, HttpUrl
from sqlmodel import Session, select
from ..auth import current_user
from ..db import get_session
from ..config import settings as config
from ..models import Experience, Post, Project, ProjectMember, PublicUser, User
from ..services.profile_settings import Preferences, preferences, settings_record
from ..services.skills import normalize, skill_graph
from .auth import password_hasher
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.exc import IntegrityError

router = APIRouter(tags=['settings'])


class ProfileEdit(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bio: str = Field(default='', max_length=500)
    major: str = Field(default='', max_length=100)
    year: str = Field(default='', max_length=30)
    company: str = Field(default='', max_length=100)
    title: str = Field(default='', max_length=100)
    avatar_url: str = Field(default='', max_length=1000)

    @field_validator('name', mode='before')
    @classmethod
    def name_trim(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('avatar_url')
    @classmethod
    def avatar_link(cls, value):
        if value and HttpUrl(value).scheme != 'https':
            raise ValueError('Use an https:// avatar URL')
        return value


class SettingsEdit(BaseModel):
    profile: ProfileEdit
    preferences: Preferences


def account_info(session, user):
    record = settings_record(session, user.id)
    return dict(username=user.username, email=user.email, has_password=bool(user.password_hash), github_connected=bool(user.github_token), google_connected=bool(record.google_sub), google_email=record.google_email, github_available=bool(config.github_client_id), google_available=bool(config.google_client_id))


@router.get('/me/settings')
def get_settings(user: User = Depends(current_user), session: Session = Depends(get_session)):
    mids = session.exec(select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)).all()
    prefs = preferences(session, user.id)
    posts = list(session.exec(select(Post).where(Post.author_id == user.id).order_by(Post.created_at.desc(), Post.id.desc()).limit(50)).all())
    if prefs.pinned_post_id and all(post.id != prefs.pinned_post_id for post in posts):
        pinned = session.get(Post, prefs.pinned_post_id)
        if pinned and pinned.author_id == user.id:
            posts.insert(0, pinned)
    return dict(user=PublicUser.model_validate(user), preferences=prefs, account=account_info(session, user),
        projects=session.exec(select(Project).where((Project.owner_id == user.id) | Project.id.in_(mids))).all(),
        posts=posts,
        experience=session.exec(select(Experience).where(Experience.user_id == user.id)).all())


@router.put('/me/settings')
def save_settings(body: SettingsEdit, user: User = Depends(current_user), session: Session = Depends(get_session)):
    for pid in body.preferences.pinned_project_ids:
        project = session.get(Project, pid)
        if not project or (project.owner_id != user.id and not session.get(ProjectMember, (pid, user.id))):
            raise HTTPException(403, 'You can only pin projects you participate in')
    if body.preferences.pinned_post_id is not None:
        post = session.get(Post, body.preferences.pinned_post_id)
        if not post or post.author_id != user.id:
            raise HTTPException(403, 'You can only pin your own posts')
    available = {node['skill'] for node in skill_graph(session, user)['nodes']}
    highlighted = []
    for skill in body.preferences.highlighted_skills:
        normalized = normalize(skill)
        if not normalized or normalized not in available:
            raise HTTPException(422, f'Choose a skill already on your graph: {skill}')
        if normalized not in highlighted:
            highlighted.append(normalized)
    body.preferences.highlighted_skills = highlighted
    record = settings_record(session, user.id)
    record.data = body.preferences.model_dump()
    for key, value in body.profile.model_dump().items():
        setattr(user, key, value.strip() if isinstance(value, str) else value)
    session.add_all([user, record]); session.commit()
    return {'saved': True}


class ExperienceEdit(BaseModel):
    kind: Literal['work', 'education']
    title: str = Field(min_length=1, max_length=200)
    org: str = Field(min_length=1, max_length=200)
    start: str = Field(default='', max_length=50)
    end: str = Field(default='', max_length=50)
    summary: str = Field(default='', max_length=2000)
    skills: list[str] = Field(default_factory=list, max_length=50)


@router.put('/me/experience/{entry_id}')
def edit_experience(entry_id: int, body: ExperienceEdit, user: User = Depends(current_user), session: Session = Depends(get_session)):
    entry = session.get(Experience, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, 'Experience not found')
    skills = [normalize(skill) for skill in body.skills]
    if None in skills:
        raise HTTPException(422, 'Choose skills from the skill vocabulary')
    for key, value in body.model_dump().items():
        setattr(entry, key, skills if key == 'skills' else value)
    session.add(entry); session.commit(); session.refresh(entry)
    return entry


@router.delete('/me/experience/{entry_id}', status_code=204)
def delete_experience(entry_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    entry = session.get(Experience, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, 'Experience not found')
    session.delete(entry); session.commit()


@router.delete('/me/resume', status_code=204)
def remove_resume(user: User = Depends(current_user), session: Session = Depends(get_session)):
    for entry in session.exec(select(Experience).where(Experience.user_id == user.id)).all():
        session.delete(entry)
    session.commit()


class PasswordEdit(BaseModel):
    current_password: str = Field(default='', max_length=128)
    new_password: str = Field(min_length=12, max_length=128)
    username: str = Field(min_length=3, max_length=50)


@router.put('/me/password', status_code=204)
def change_password(body: PasswordEdit, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if user.password_hash:
        try:
            valid = password_hasher.verify(body.current_password, user.password_hash)
        except (ValueError, UnknownHashError):
            valid = False
        if not valid:
            raise HTTPException(403, 'Current password is incorrect')
    username = body.username.strip()
    if len(username) < 3:
        raise HTTPException(422, 'Username must be at least three characters')
    existing = session.exec(select(User).where(User.username == username, User.id != user.id)).first()
    if existing:
        raise HTTPException(409, 'Username already in use')
    user.username = username
    user.password_hash = password_hasher.hash(body.new_password)
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, 'Username already in use')


@router.delete('/me/connections/{provider}', status_code=204)
def disconnect(provider: Literal['github', 'google'], user: User = Depends(current_user), session: Session = Depends(get_session)):
    record = settings_record(session, user.id)
    other = bool(record.google_sub) if provider == 'github' else bool(user.github_token)
    if not (user.password_hash and user.username) and not other:
        raise HTTPException(409, 'Set a password or connect another sign-in method first')
    if provider == 'github':
        user.github_token = None; user.github_username = None
        session.add(user)
    else:
        record.google_sub = None
        session.add(record)
    session.commit()
