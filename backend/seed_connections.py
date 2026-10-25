"""Create student1-5, faculty1-5, mentor1-5 and an accepted network with Adi.

Run with --adi-user-id ID --apply. Without --apply the transaction is rolled back.
Fictional profiles have no login credentials. Existing real accounts are never reused.
"""
import argparse
from itertools import combinations
from sqlmodel import Session, select
from app.db import engine
from app.models import ConnectionRequest, Message, Thread, ThreadMember, User, now

SAMPLES = [(f'{role}{index}', role) for role in ('student', 'faculty', 'mentor') for index in range(1, 6)]
BIO = 'Fictional sample account for the connections graph.'


def seed(session: Session, adi_id: int):
    adi = session.get(User, adi_id)
    if not adi:
        raise RuntimeError('Adi account not found; no changes committed')
    counts = dict(users=0, connections=0, threads=0, messages=0)
    people = [adi]
    for username, role in SAMPLES:
        email = f'{username}@connections.keystone.test'
        person = session.exec(select(User).where(User.username == username)).first()
        if person and (person.email != email or person.bio != BIO or person.role != role or person.password_hash or person.github_token or person.is_admin):
            raise RuntimeError(f'{username} belongs to an existing non-sample account; no changes committed')
        if not person:
            person = User(username=username, name=username, email=email, role=role, bio=BIO)
            session.add(person)
            session.flush()
            counts['users'] += 1
        people.append(person)
    if len({person.id for person in people}) != 16:
        raise RuntimeError('The target must be separate from the 15 sample users')
    for sender, recipient in combinations(people, 2):
        low, high = sorted((sender.id, recipient.id))
        existing = session.exec(select(ConnectionRequest).where(ConnectionRequest.low_id == low, ConnectionRequest.high_id == high)).first()
        if existing:
            if existing.status != 'accepted':
                raise RuntimeError('A pair has an unanswered or denied request; no changes committed')
            continue
        thread = None
        for tid in session.exec(select(ThreadMember.thread_id).where(ThreadMember.user_id == sender.id)).all():
            members = set(session.exec(select(ThreadMember.user_id).where(ThreadMember.thread_id == tid)).all())
            if members == {sender.id, recipient.id}:
                thread = session.get(Thread, tid)
                break
        if thread is None:
            thread = Thread()
            session.add(thread)
            session.flush()
            session.add_all([ThreadMember(thread_id=thread.id, user_id=person.id) for person in (sender, recipient)])
            counts['threads'] += 1
        message = Message(thread_id=thread.id, sender_id=sender.id, body='Follow request accepted. You are now connected.')
        session.add(message)
        session.flush()
        session.add(ConnectionRequest(low_id=low, high_id=high, sender_id=sender.id, recipient_id=recipient.id, thread_id=thread.id, message_id=message.id, status='accepted', responded_at=now()))
        session.flush()
        counts['connections'] += 1
        counts['messages'] += 1
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adi-user-id', type=int, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    # Only create the additive new table; do not alter existing accounts or schema.
    ConnectionRequest.__table__.create(engine, checkfirst=True)
    with Session(engine) as session:
        counts = seed(session, args.adi_user_id)
        if args.apply:
            session.commit()
            print('Committed:', counts)
        else:
            session.rollback()
            print('Preview (rolled back):', counts)
