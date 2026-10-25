from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from ..auth import current_user
from ..db import get_session
from ..models import (
    Comment,
    Endorsement,
    HelpRequest,
    Invite,
    LogEntry,
    Post,
    Project,
    ProjectMember,
    PublicUser,
    User,
)
from ..services import ai, github
from ..services.profile_settings import public_user

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

def require_member(session: Session, project_id: int, user: User) -> None:
    project = get_project(session, project_id)
    if project.owner_id != user.id and not session.get(ProjectMember, (project_id, user.id)):
        raise HTTPException(403, "Join this project first")


@router.get("")
def list_projects(q: str = "", tag: str = "", status: str = "active", session: Session = Depends(get_session)):
    statement = select(Project).where(Project.status == status)
    statement = statement.order_by(Project.end_date.desc(), Project.created_at.desc(), Project.id.desc()) if status == "archived" else statement.order_by(Project.created_at.desc())
    projects = session.exec(statement).all()
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
    session.refresh(project)  # the second commit expires it; without this the API returns {}
    return project


@router.get("/{project_id}")
def project_detail(project_id: int, session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    member_rows = session.exec(select(ProjectMember).where(ProjectMember.project_id == project_id)).all()
    members = [
        {"role": m.role, "user": public_user(session, session.get(User, m.user_id))} for m in member_rows
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


@router.put("/{project_id}", response_model=Project)
def update_project(project_id: int, body: ProjectIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    require_member(session, project_id, user)
    if not body.title.strip():
        raise HTTPException(422, "Project title is required")
    for key, value in body.model_dump().items():
        setattr(project, key, value)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def project_participants(session: Session, project: Project) -> set[int]:
    return {project.owner_id} | set(session.exec(select(ProjectMember.user_id).where(ProjectMember.project_id == project.id)).all())


@router.post("/{project_id}/leave", status_code=204)
def leave_project(project_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    require_member(session, project_id, user)
    remaining = project_participants(session, project) - {user.id}
    if not remaining:
        raise HTTPException(409, "You are the only participant. Delete this project instead.")
    if project.owner_id == user.id:
        project.owner_id = min(remaining)
        successor = session.get(ProjectMember, (project_id, project.owner_id))
        successor.role = "owner"
        session.add(successor)
        session.add(project)
    member = session.get(ProjectMember, (project_id, user.id))
    if member:
        session.delete(member)
    session.commit()


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    require_member(session, project_id, user)
    if project.owner_id != user.id:
        raise HTTPException(403, "Only the owner can delete a project")
    if len(project_participants(session, project)) > 1:
        raise HTTPException(409, "This is a group project. Leave it instead of deleting it.")
    logs = session.exec(select(LogEntry).where(LogEntry.project_id == project_id)).all()
    posts = session.exec(select(Post).where((Post.project_id == project_id) | Post.log_entry_id.in_([row.id for row in logs]))).all()
    requests = session.exec(select(HelpRequest).where(HelpRequest.project_id == project_id)).all()
    for row in session.exec(select(Comment).where((Comment.project_id == project_id) | Comment.post_id.in_([row.id for row in posts]))).all():
        session.delete(row)
    for row in session.exec(select(Endorsement).where((Endorsement.project_id == project_id) | Endorsement.help_request_id.in_([row.id for row in requests]))).all():
        session.delete(row)
    session.flush()
    for row in posts + requests:
        session.delete(row)
    session.flush()
    for row in logs:
        session.delete(row)
    for model in (Invite, ProjectMember):
        for row in session.exec(select(model).where(model.project_id == project_id)).all():
            session.delete(row)
    session.flush()
    session.delete(project)
    session.commit()



@router.post("/{project_id}/invite", response_model=Invite)
def invite(project_id: int, to_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    get_project(session, project_id)
    require_member(session, project_id, user)
    require_active(session, project_id)
    if to_id == user.id:
        raise HTTPException(400, "You can't invite yourself")
    if not session.get(User, to_id):
        raise HTTPException(404, "User not found")
    if session.get(ProjectMember, (project_id, to_id)):
        raise HTTPException(409, "They're already on this project")
    pending = session.exec(
        select(Invite).where(Invite.project_id == project_id, Invite.to_id == to_id, Invite.status == "pending")
    ).first()
    if pending:
        raise HTTPException(409, "Invite already sent")
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
    if project.status != "archived":
        project.status = "archived"
        project.end_date = date.today().isoformat()
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.post("/{project_id}/reopen", response_model=Project)
def reopen(project_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    if project.owner_id != user.id:
        raise HTTPException(403, "Only the owner can reopen a project")
    if project.status == "archived":
        project.status = "active"
        project.end_date = None
        session.add(project)
        session.commit()
    session.refresh(project)
    return project


def require_active(session: Session, project_id: int) -> None:
    if get_project(session, project_id).status != "active":
        raise HTTPException(409, "This project is archived. The owner must reopen it before adding new activity.")


# ---- Auto-docs -------------------------------------------------------------


@router.post("/{project_id}/logs/draft")
def draft_log(project_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Pull commits since the last log and ask Claude for a draft. Nothing is saved."""
    project = get_project(session, project_id)
    require_member(session, project_id, user)
    require_active(session, project_id)
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
        draft = ai.draft_log(project.title, project.description, commits, readme)
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
    require_member(session, project_id, user)
    require_active(session, project_id)
    entry = LogEntry(project_id=project_id, author_id=user.id, **body.model_dump())
    session.add(entry)
    session.commit()
    session.refresh(entry)
    session.add(Post(author_id=user.id, project_id=project_id, log_entry_id=entry.id, body=entry.title, type="log"))
    session.commit()
    session.refresh(entry)
    return entry


@router.get("/{project_id}/logs")
def list_logs(project_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(LogEntry).where(LogEntry.project_id == project_id, LogEntry.published).order_by(LogEntry.created_at.desc())
    ).all()


def editable_log(session: Session, project_id: int, log_id: int, user: User) -> LogEntry:
    require_member(session, project_id, user)
    entry = session.get(LogEntry, log_id)
    if not entry or entry.project_id != project_id:
        raise HTTPException(404, "Weekly log not found")
    if entry.author_id != user.id:
        raise HTTPException(403, "Only the author can edit or delete this weekly log")
    return entry


@router.put("/{project_id}/logs/{log_id}", response_model=LogEntry)
def update_log(project_id: int, log_id: int, body: LogIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    entry = editable_log(session, project_id, log_id, user)
    if not body.title.strip() or not body.week_label.strip():
        raise HTTPException(422, "A title and week label are required")
    # Authorship, project, creation date and commit provenance remain unchanged.
    for key in ("week_label", "title", "built", "learned", "stuck", "skills"):
        setattr(entry, key, getattr(body, key))
    session.add(entry)
    for post in session.exec(select(Post).where(Post.log_entry_id == log_id)).all():
        post.body = entry.title
        session.add(post)
    session.commit()
    session.refresh(entry)
    return entry


@router.delete("/{project_id}/logs/{log_id}", status_code=204)
def delete_log(project_id: int, log_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    entry = editable_log(session, project_id, log_id, user)
    posts = session.exec(select(Post).where(Post.log_entry_id == log_id)).all()
    for comment in session.exec(select(Comment).where(Comment.post_id.in_([post.id for post in posts]))).all():
        session.delete(comment)
    session.flush()
    for post in posts:
        session.delete(post)
    session.flush()
    session.delete(entry)
    session.commit()
