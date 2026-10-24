"""Database tables. Lists are stored as JSON columns to keep the schema simple.

Keep frontend/src/lib/types.ts in sync when you change a field here.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


def json_list():
    return Field(default_factory=list, sa_column=Column(JSON))


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    username: Optional[str] = Field(
        default=None,
        index=True,
        unique=True,
        min_length=3,
        max_length=50,
    )
    password_hash: Optional[str] = None  # GitHub and demo users have no local password.

    role: str = "student"  # student | mentor | faculty
    name: str
    email: Optional[str] = Field(default=None, unique=True, index=True)
    major: Optional[str] = None
    year: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    github_username: Optional[str] = Field(default=None, index=True)
    github_token: Optional[str] = None  # never return this; use PublicUser
    expertise_tags: list[str] = json_list()
    created_at: datetime = Field(default_factory=now)


class PublicUser(SQLModel):
    """What the API returns for a user (no token)."""

    id: int
    role: str
    name: str
    major: Optional[str] = None
    year: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    github_username: Optional[str] = None
    expertise_tags: list[str] = []


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    title: str
    description: str = ""
    repo_full_name: Optional[str] = None  # "owner/repo"
    tags: list[str] = json_list()
    looking_for: list[str] = json_list()
    status: str = "active"  # active | archived
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_at: datetime = Field(default_factory=now)


class ProjectMember(SQLModel, table=True):
    project_id: int = Field(foreign_key="project.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    role: str = "member"


class Invite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    from_id: int = Field(foreign_key="user.id")
    to_id: int = Field(foreign_key="user.id")
    status: str = "pending"  # pending | accepted | declined
    created_at: datetime = Field(default_factory=now)


class LogEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    author_id: int = Field(foreign_key="user.id")
    week_label: str
    title: str
    built: list[str] = json_list()
    learned: list[str] = json_list()
    stuck: list[str] = json_list()
    skills: list[str] = json_list()
    commit_shas: list[str] = json_list()
    source: str = "ai"  # ai | manual
    published: bool = True
    created_at: datetime = Field(default_factory=now)


class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="user.id")
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    log_entry_id: Optional[int] = Field(default=None, foreign_key="logentry.id")
    body: str
    type: str = "update"  # update | log | question
    created_at: datetime = Field(default_factory=now)


class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="user.id")
    post_id: Optional[int] = Field(default=None, foreign_key="post.id")
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    body: str
    created_at: datetime = Field(default_factory=now)


class HelpRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    requester_id: int = Field(foreign_key="user.id")
    question: str
    tags: list[str] = json_list()
    minutes: int = 15  # 5 | 15 | 30
    status: str = "open"  # open | answered | resolved
    mentor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    answer: Optional[str] = None
    helpful: Optional[bool] = None
    created_at: datetime = Field(default_factory=now)


class Endorsement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    from_id: int = Field(foreign_key="user.id")
    to_id: int = Field(foreign_key="user.id", index=True)
    skill: str
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    help_request_id: Optional[int] = Field(default=None, foreign_key="helprequest.id")
    note: str = ""
    created_at: datetime = Field(default_factory=now)


class Thread(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now)


class ThreadMember(SQLModel, table=True):
    thread_id: int = Field(foreign_key="thread.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="thread.id", index=True)
    sender_id: int = Field(foreign_key="user.id")
    body: str
    created_at: datetime = Field(default_factory=now)


class Experience(SQLModel, table=True):
    """A job or school from the user's uploaded resume (self-reported)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    kind: str = "work"  # work | education
    title: str  # role, or degree for education
    org: str
    start: str = ""  # as written on the resume, e.g. "May 2025"
    end: str = ""  # "" or "Present" when ongoing
    summary: str = ""
