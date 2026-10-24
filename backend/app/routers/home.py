"""Small, personalized next steps for the home sidebar."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..auth import current_user
from ..db import get_session
from ..models import HelpRequest, LogEntry, Project, ProjectMember, User
from ..services.skills import skill_graph
from .help import match_score

router = APIRouter(tags=['home'])


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@router.get('/home/sidebar')
def sidebar(user: User = Depends(current_user), session: Session = Depends(get_session)):
    projects = session.exec(select(Project).where(Project.status == 'active')).all()
    member_ids = set(session.exec(select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)).all())
    mine = [project for project in projects if project.owner_id == user.id or project.id in member_ids]
    my_ids = {project.id for project in mine}
    logs = session.exec(select(LogEntry).where(LogEntry.project_id.in_(my_ids), LogEntry.published).order_by(LogEntry.created_at.desc(), LogEntry.id.desc())).all() if my_ids else []
    latest = {}
    own_latest = {}
    for log in logs:
        latest.setdefault(log.project_id, log)
        if log.author_id == user.id:
            own_latest.setdefault(log.project_id, log)
    now = datetime.now(timezone.utc)
    mine.sort(key=lambda project: (utc(latest[project.id].created_at if project.id in latest else project.created_at), project.id), reverse=True)
    my_projects = [dict(project=project, latest_log_title=latest[project.id].title if project.id in latest else None,
        last_activity_at=latest[project.id].created_at if project.id in latest else project.created_at,
        needs_log=project.id not in own_latest or utc(own_latest[project.id].created_at) <= now - timedelta(days=7)) for project in mine[:3]]
    skills = {node['skill'].casefold() for node in skill_graph(session, user)['nodes'] if node['tier'] not in ('category', 'derived')}
    candidates = []
    for project in projects:
        if project.id in my_ids or not any(role.strip() for role in project.looking_for):
            continue
        matches = list(dict.fromkeys(tag for tag in project.tags if tag.casefold() in skills))
        candidates.append(dict(project=project, matched_skills=matches))
    candidates.sort(key=lambda item: (len(item['matched_skills']), utc(item['project'].created_at), item['project'].id), reverse=True)
    help_requests = []
    if user.role in ('mentor', 'faculty'):
        active_ids = {project.id for project in projects}
        requests = session.exec(select(HelpRequest).where(HelpRequest.status == 'open', HelpRequest.requester_id != user.id, HelpRequest.project_id.in_(active_ids))).all() if active_ids else []
        requests = sorted(requests, key=lambda request: (match_score(request, user), utc(request.created_at), request.id), reverse=True)
        help_requests = [dict(request=request, matched_skills=[tag for tag in request.tags if tag.casefold() in skills]) for request in requests[:3]]
    return dict(my_projects=my_projects, active_project_count=len(mine), opportunities=candidates[:3], help_requests=help_requests)
