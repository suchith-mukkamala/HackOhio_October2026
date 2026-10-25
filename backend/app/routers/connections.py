"""Follow requests become mutual connections only after the recipient accepts."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select
from ..auth import current_user
from ..db import get_session
from ..models import ConnectionRequest, Message, Thread, ThreadMember, User, now
from ..services.profile_settings import may_contact, public_user

router = APIRouter(prefix='/connections', tags=['connections'])


def request_data(request: ConnectionRequest):
    return request.model_dump(mode='json')


def pair_request(session: Session, a: int, b: int):
    low, high = sorted((a, b))
    return session.exec(select(ConnectionRequest).where(ConnectionRequest.low_id == low, ConnectionRequest.high_id == high)).first()


@router.get('')
def connections(user: User = Depends(current_user), session: Session = Depends(get_session)):
    requests = session.exec(select(ConnectionRequest).where(or_(ConnectionRequest.sender_id == user.id, ConnectionRequest.recipient_id == user.id)).order_by(ConnectionRequest.created_at.desc(), ConnectionRequest.id.desc())).all()
    people = []
    visible_requests = []
    for request in requests:
        other = session.get(User, request.recipient_id if request.sender_id == user.id else request.sender_id)
        if not other:
            continue
        person = public_user(session, other, user)
        if request.status == 'accepted':
            people.append(person)
        else:
            visible_requests.append(dict(**request_data(request), user=person))
    # Only expose accepted edges whose two endpoints are already the viewer's connections.
    ids = [person.id for person in people]
    edges = session.exec(select(ConnectionRequest).where(ConnectionRequest.status == 'accepted', ConnectionRequest.low_id.in_(ids), ConnectionRequest.high_id.in_(ids)).order_by(ConnectionRequest.low_id, ConnectionRequest.high_id)).all() if ids else []
    return dict(connections=people, requests=visible_requests, interconnections=[dict(source=edge.low_id, target=edge.high_id) for edge in edges])


@router.get('/users/{user_id}')
def relationship(user_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if not session.get(User, user_id):
        raise HTTPException(404, 'User not found')
    request = pair_request(session, user.id, user_id)
    return request_data(request) if request else None


@router.post('/users/{user_id}')
def request_follow(user_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if user_id == user.id:
        raise HTTPException(400, 'You cannot follow yourself')
    if not session.get(User, user_id):
        raise HTTPException(404, 'User not found')
    existing = pair_request(session, user.id, user_id)
    if existing:
        return request_data(existing)
    if not may_contact(session, user.id, user_id, False):
        raise HTTPException(403, 'This person’s messaging preferences do not allow follow requests')
    # Exact membership prevents a private request from appearing in a group conversation.
    thread = None
    for tid in session.exec(select(ThreadMember.thread_id).where(ThreadMember.user_id == user.id)).all():
        members = set(session.exec(select(ThreadMember.user_id).where(ThreadMember.thread_id == tid)).all())
        if members == {user.id, user_id}:
            thread = session.get(Thread, tid)
            break
    if thread is None:
        thread = Thread()
        session.add(thread)
        session.flush()
        session.add_all([ThreadMember(thread_id=thread.id, user_id=uid) for uid in (user.id, user_id)])
    message = Message(thread_id=thread.id, sender_id=user.id, body='Requested to follow.')
    session.add(message)
    session.flush()
    request = ConnectionRequest(low_id=min(user.id, user_id), high_id=max(user.id, user_id), sender_id=user.id, recipient_id=user_id, thread_id=thread.id, message_id=message.id)
    session.add(request)
    try:
        session.commit()
    except IntegrityError:
        # Concurrent/repeated requests must not leave extra messages or threads.
        session.rollback()
        existing = pair_request(session, user.id, user_id)
        if existing:
            return request_data(existing)
        raise
    session.refresh(request)
    return request_data(request)


class Decision(SQLModel):
    status: Literal['accepted', 'denied']


@router.post('/requests/{request_id}/respond')
def respond(request_id: int, body: Decision, user: User = Depends(current_user), session: Session = Depends(get_session)):
    request = session.get(ConnectionRequest, request_id)
    if not request:
        raise HTTPException(404, 'Follow request not found')
    if request.recipient_id != user.id:
        raise HTTPException(403, 'Only the recipient can respond to this request')
    if request.status != 'pending':
        if request.status == body.status:
            return request_data(request)
        raise HTTPException(409, 'This follow request has already been answered')
    result = session.execute(update(ConnectionRequest).where(ConnectionRequest.id == request_id, ConnectionRequest.status == 'pending').values(status=body.status, responded_at=now()))
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'This follow request has already been answered')
    message = session.get(Message, request.message_id)
    message.body = 'Follow request accepted. You are now connected.' if body.status == 'accepted' else 'Follow request denied.'
    session.add(message)
    session.commit()
    session.refresh(request)
    return request_data(request)


def message_data(session: Session, message: Message):
    request = session.exec(select(ConnectionRequest).where(ConnectionRequest.message_id == message.id)).first()
    return message_payload(message, request)


def message_payload(message: Message, request: ConnectionRequest | None):
    data = message.model_dump(mode='json')
    if request:
        data['follow_request'] = request_data(request)
    return data


def thread_messages_data(session: Session, thread_id: int):
    requests = {request.message_id: request for request in session.exec(select(ConnectionRequest).where(ConnectionRequest.thread_id == thread_id)).all()}
    messages = session.exec(select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at, Message.id)).all()
    return [message_payload(message, requests.get(message.id)) for message in messages]
