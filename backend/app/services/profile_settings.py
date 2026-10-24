"""Validated profile preferences and shared permission rules."""
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlmodel import Session, select
from ..models import ProfileSettingsRecord, Project, ProjectMember, PublicUser, User


class Preferences(BaseModel):
    availability: Literal['not_looking', 'teammates', 'projects', 'mentorship', 'available_to_mentor'] = 'not_looking'
    preferred_roles: list[str] = Field(default_factory=list, max_length=20)
    interests: list[str] = Field(default_factory=list, max_length=30)
    hours_per_week: int = Field(default=0, ge=0, le=80)
    website: str = Field(default='', max_length=500)
    linkedin: str = Field(default='', max_length=500)
    contact_email: str = Field(default='', max_length=254)
    show_experience: bool = True
    show_activity: bool = True
    show_contact: bool = True
    direct_messages: Literal['everyone', 'teammates', 'nobody'] = 'everyone'
    group_invites: Literal['everyone', 'teammates', 'nobody'] = 'everyone'
    particles: bool = True
    reduce_motion: bool = False
    highlighted_skills: list[str] = Field(default_factory=list, max_length=10)
    pinned_project_ids: list[int] = Field(default_factory=list, max_length=6)
    pinned_post_id: int | None = None

    @field_validator('website', 'linkedin')
    @classmethod
    def safe_link(cls, value):
        value = value.strip()
        if value:
            parsed = HttpUrl(value)
            if parsed.scheme != 'https':
                raise ValueError('Use an https:// link')
        return value

    @field_validator('contact_email')
    @classmethod
    def safe_email(cls, value):
        if value:
            from pydantic import TypeAdapter, EmailStr
            return str(TypeAdapter(EmailStr).validate_python(value))
        return ''


def preferences(session: Session, user_id: int) -> Preferences:
    record = session.get(ProfileSettingsRecord, user_id)
    return Preferences.model_validate(record.data if record else {})


def settings_record(session: Session, user_id: int) -> ProfileSettingsRecord:
    return session.get(ProfileSettingsRecord, user_id) or ProfileSettingsRecord(user_id=user_id)


def public_preferences(session: Session, user_id: int, own: bool = False) -> dict:
    data = preferences(session, user_id).model_dump()
    for key in ('direct_messages', 'group_invites', 'particles', 'reduce_motion'):
        data.pop(key)
    if not own and not data['show_contact']:
        for key in ('website', 'linkedin', 'contact_email'):
            data[key] = ''
    return data


def public_user(session: Session, user: User, viewer: User | None = None):
    result = PublicUser.model_validate(user)
    if (not viewer or viewer.id != user.id) and not preferences(session, user.id).show_contact:
        result.github_username = None
    return result


def teammates(session: Session, first: int, second: int) -> bool:
    def projects(uid):
        return set(session.exec(select(ProjectMember.project_id).where(ProjectMember.user_id == uid)).all()) | set(session.exec(select(Project.id).where(Project.owner_id == uid)).all())
    return bool(projects(first) & projects(second))


def may_contact(session: Session, sender: int, recipient: int, group: bool) -> bool:
    settings = preferences(session, recipient)
    rule = settings.group_invites if group else settings.direct_messages
    return rule == 'everyone' or (rule == 'teammates' and teammates(session, sender, recipient))
