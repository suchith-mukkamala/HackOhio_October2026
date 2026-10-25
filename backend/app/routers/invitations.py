"""Private project invitations and consent-based team membership."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select
from ..auth import current_user
from ..db import get_session
from ..models import Invite, Project, ProjectMember, User
from ..services.profile_settings import public_user

router = APIRouter(prefix='/project-invites', tags=['projects'])


@router.get('')
def received(user: User = Depends(current_user), session: Session = Depends(get_session)):
    result = []
    for invite in session.exec(select(Invite).where(Invite.to_id == user.id).order_by(Invite.created_at.desc(), Invite.id.desc())).all():
        project = session.get(Project, invite.project_id)
        sender = session.get(User, invite.from_id)
        if project and sender:
            result.append(dict(**invite.model_dump(mode='json'), project=project, sender=public_user(session, sender, user)))
    return result


class InviteDecision(SQLModel):
    status: Literal['accepted', 'declined']


@router.post('/{invite_id}/respond', response_model=Invite)
def respond(invite_id: int, body: InviteDecision, user: User = Depends(current_user), session: Session = Depends(get_session)):
    invite = session.get(Invite, invite_id)
    if not invite:
        raise HTTPException(404, 'Invitation not found')
    if invite.to_id != user.id:
        raise HTTPException(403, 'Only the invited person can respond')
    if invite.status != 'pending':
        if invite.status == body.status:
            return invite
        raise HTTPException(409, 'This invitation has already been answered')
    project = session.get(Project, invite.project_id)
    if not project:
        raise HTTPException(404, 'Project not found')
    if body.status == 'accepted' and project.status != 'active':
        raise HTTPException(409, 'This project is archived and is not accepting new participants')
    result = session.execute(update(Invite).where(Invite.id == invite_id, Invite.status == 'pending').values(status=body.status))
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'This invitation has already been answered')
    if body.status == 'accepted' and project.owner_id != user.id and not session.get(ProjectMember, (project.id, user.id)):
        session.add(ProjectMember(project_id=project.id, user_id=user.id, role='member'))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, 'Project membership changed. Refresh and try again.')
    session.refresh(invite)
    return invite
