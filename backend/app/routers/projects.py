from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from ..auth import current_user
from ..db import get_session
from ..models import (
    Comment,
    HelpRequest,
    Invite,
    LogEntry,
    Post,
    Project,
    ProjectMember,
    PublicUser,
    User,
)
from ..services import claude, github

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectIn(SQLModel):
    title: str
    description: str = ""
    repo_full_name: Optional[str] = None
    tags: list[str] = []
    looking_for: list[str] = []
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class LogIn(SQLModel):
    week_label: str
    title: str
    built: list[str] = []
    learned: list[str] = []
    stuck: list[str] = []
    skills: list[str] = []
    commit_shas: list[str] = []
    source: str = "ai"


def get_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("")
def list_projects(q: str = "", tag: str = "", status: str = "active", session: Session = Depends(get_session)):
    projects = session.exec(select(Project).where(Project.status == status).order_by(Project.created_at.desc())).all()
    if q:
        projects = [p for p in projects if q.lower() in (p.title + " " + p.description).lower()]
    if tag:
        projects = [p for p in projects if tag.lower() in (t.lower() for t in p.tags)]
    return projects


@router.post("", response_model=Project)
def create_project(body: ProjectIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if user.role != "student":
        raise HTTPException(403, "Only students can publish projects")
    project = Project(owner_id=user.id, **body.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    session.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    session.commit()
    return project


@router.get("/{project_id}")
def project_detail(project_id: int, session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    member_rows = session.exec(select(ProjectMember).where(ProjectMember.project_id == project_id)).all()
    members = [
        {"role": m.role, "user": PublicUser.model_validate(session.get(User, m.user_id))} for m in member_rows
    ]
    timeline = session.exec(
        select(LogEntry)
        .where(LogEntry.project_id == project_id, LogEntry.published)
        .order_by(LogEntry.created_at.desc())
    ).all()
    help_requests = session.exec(select(HelpRequest).where(HelpRequest.project_id == project_id)).all()
    comments = session.exec(select(Comment).where(Comment.project_id == project_id)).all()
    return {
        "project": project,
        "members": members,
        "timeline": timeline,
        "help_requests": help_requests,
        "comments": comments,
    }


@router.post("/{project_id}/invite", response_model=Invite)
def invite(project_id: int, to_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    get_project(session, project_id)
    inv = Invite(project_id=project_id, from_id=user.id, to_id=to_id)
    session.add(inv)
    session.commit()
    session.refresh(inv)
    return inv


@router.post("/{project_id}/archive", response_model=Project)
def archive(project_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    if project.owner_id != user.id:
        raise HTTPException(403, "Only the owner can archive a project")
    project.status = "archived"
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


# ---- Auto-docs -------------------------------------------------------------


@router.post("/{project_id}/logs/draft")
def draft_log(project_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Pull commits since the last log and ask Claude for a draft. Nothing is saved."""
    project = get_project(session, project_id)
    if not project.repo_full_name:
        raise HTTPException(400, "Link a GitHub repo to this project first")
    last = session.exec(
        select(LogEntry).where(LogEntry.project_id == project_id).order_by(LogEntry.created_at.desc())
    ).first()
    since = last.created_at.isoformat() if last else None

    commits = github.recent_commits(user.github_token, project.repo_full_name, since=since)
    if not commits:
        raise HTTPException(400, "No new commits since the last log")
    readme = github.readme(user.github_token, project.repo_full_name)
    try:
        draft = claude.draft_log(project.title, project.description, commits, readme)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return {
        **draft.model_dump(),
        "week_label": f"Week of {date.today():%b %d}",
        "commit_shas": [c["sha"] for c in commits],
        "source": "ai",
    }


@router.post("/{project_id}/logs", response_model=LogEntry)
def publish_log(
    project_id: int, body: LogIn, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    """Save the (edited) draft to the timeline and share it to the feed."""
    get_project(session, project_id)
    entry = LogEntry(project_id=project_id, author_id=user.id, **body.model_dump())
    session.add(entry)
    session.commit()
    session.refresh(entry)
    session.add(Post(author_id=user.id, project_id=project_id, log_entry_id=entry.id, body=entry.title, type="log"))
    session.commit()
    return entry


@router.get("/{project_id}/logs")
def list_logs(project_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(LogEntry).where(LogEntry.project_id == project_id).order_by(LogEntry.created_at.desc())
    ).all()
