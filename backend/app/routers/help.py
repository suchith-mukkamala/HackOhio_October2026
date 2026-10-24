from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from ..auth import current_user
from ..db import get_session
from ..models import Endorsement, HelpRequest, User
from ..services.skills import normalize
from .projects import require_member

router = APIRouter(prefix="/help", tags=["help"])


class HelpIn(SQLModel):
    project_id: int
    question: str
    tags: list[str] = []
    minutes: int = 15


class AnswerIn(SQLModel):
    answer: str
    endorse_skill: Optional[str] = None
    endorse_note: str = ""


def match_score(request: HelpRequest, mentor: User) -> float:
    """Tag overlap with the mentor's expertise, plus a nudge for small time asks."""
    req = {t.lower() for t in request.tags}
    have = {t.lower() for t in mentor.expertise_tags}
    overlap = len(req & have) / max(len(req), 1)
    quick_bonus = {5: 0.2, 15: 0.1}.get(request.minutes, 0)
    return round(overlap + quick_bonus, 2)


@router.post("", response_model=HelpRequest)
def ask(body: HelpIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if body.minutes not in (5, 15, 30):
        raise HTTPException(400, "Time ask must be 5, 15 or 30 minutes")
    if not body.question.strip():
        raise HTTPException(400, "Write your question first")
    require_member(session, body.project_id, user)
    req = HelpRequest(requester_id=user.id, **body.model_dump())
    session.add(req)
    session.commit()
    session.refresh(req)
    return req


@router.get("/inbox")
def inbox(user: User = Depends(current_user), session: Session = Depends(get_session)):
    if user.role not in ("mentor", "faculty"):
        raise HTTPException(403, "The help inbox is for mentors and faculty")
    open_requests = session.exec(select(HelpRequest).where(HelpRequest.status == "open")).all()
    scored = [{**r.model_dump(), "match_score": match_score(r, user)} for r in open_requests]
    return sorted(scored, key=lambda r: r["match_score"], reverse=True)


@router.post("/{request_id}/answer", response_model=HelpRequest)
def answer(
    request_id: int, body: AnswerIn, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    if user.role not in ("mentor", "faculty"):
        raise HTTPException(403, "Only mentors and faculty can answer help requests")
    req = session.get(HelpRequest, request_id)
    if not req:
        raise HTTPException(404, "Help request not found")
    if req.requester_id == user.id:
        raise HTTPException(403, "You can't answer your own request")
    if req.status != "open":
        raise HTTPException(400, "This request has already been answered")
    if not body.answer.strip():
        raise HTTPException(400, "Write an answer first")

    skill = None
    if body.endorse_skill:
        skill = normalize(body.endorse_skill)
        if not skill:
            raise HTTPException(400, "Unknown skill. Pick one from /skills/vocabulary")

    req.answer = body.answer
    req.mentor_id = user.id
    req.status = "answered"
    session.add(req)

    if skill:
        already = session.exec(
            select(Endorsement).where(
                Endorsement.from_id == user.id,
                Endorsement.to_id == req.requester_id,
                Endorsement.skill == skill,
            )
        ).first()
        if not already:  # one endorsement per (mentor, student, skill), so scores can't be farmed
            session.add(
                Endorsement(
                    from_id=user.id,
                    to_id=req.requester_id,
                    skill=skill,
                    project_id=req.project_id,
                    help_request_id=req.id,
                    note=body.endorse_note,
                )
            )
    session.commit()
    session.refresh(req)
    return req


@router.post("/{request_id}/helpful", response_model=HelpRequest)
def helpful(request_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    req = session.get(HelpRequest, request_id)
    if not req:
        raise HTTPException(404, "Help request not found")
    if req.requester_id != user.id:
        raise HTTPException(403, "Only the person who asked can mark an answer helpful")
    if req.status != "answered":
        raise HTTPException(400, "There's no answer to rate yet")
    req.helpful = True
    req.status = "resolved"
    session.add(req)
    session.commit()
    session.refresh(req)
    return req
