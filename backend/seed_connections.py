"""Create student1-5, faculty1-5, mentor1-5 and an accepted network with Adi.

Run with --adi-user-id ID --per-role 10 --apply to expand to 10 of each role.
Without --apply the transaction is rolled back.
Fictional profiles have no login credentials. Existing real accounts are never reused.
"""
import argparse
from itertools import combinations
from sqlmodel import Session, select
from app.db import engine
from app.models import ConnectionRequest, Message, Thread, ThreadMember, User, now

SAMPLES = [(f'{role}{index}', role) for role in ('student', 'faculty', 'mentor') for index in range(1, 6)]
BIO = 'Fictional sample account for the connections graph.'


def seed(session: Session, adi_id: int, per_role: int = 5):
    if not 1 <= per_role <= 10:
        raise ValueError('Choose between 1 and 10 sample users per role')
    adi = session.get(User, adi_id)
    if not adi:
        raise RuntimeError('Adi account not found; no changes committed')
    counts = dict(users=0, connections=0, threads=0, messages=0)
    people = [adi]
    samples = [(f'{role}{index}', role) for role in ('student', 'faculty', 'mentor') for index in range(1, per_role + 1)]
    for username, role in samples:
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
    ids = {person.id for person in people}
    if len(ids) != len(samples) + 1:
        raise RuntimeError('The target must be separate from the sample users')
    existing_pairs = {(row.low_id, row.high_id): row for row in session.exec(select(ConnectionRequest).where(ConnectionRequest.low_id.in_(ids), ConnectionRequest.high_id.in_(ids))).all()}
    # Read thread memberships once, retaining outsiders so group threads cannot be reused.
    related_threads = select(ThreadMember.thread_id).where(ThreadMember.user_id.in_(ids))
    members_by_thread = {}
    for member in session.exec(select(ThreadMember).where(ThreadMember.thread_id.in_(related_threads))).all():
        members_by_thread.setdefault(member.thread_id, set()).add(member.user_id)
    direct_threads = {frozenset(members): tid for tid, members in members_by_thread.items() if len(members) == 2 and members <= ids}
    for sender, recipient in combinations(people, 2):
        low, high = sorted((sender.id, recipient.id))
        existing = existing_pairs.get((low, high))
        if existing:
            if existing.status != 'accepted':
                raise RuntimeError('A pair has an unanswered or denied request; no changes committed')
            continue
        thread_id = direct_threads.get(frozenset((sender.id, recipient.id)))
        if thread_id is None:
            thread = Thread()
            session.add(thread)
            session.flush()
            thread_id = thread.id
            session.add_all([ThreadMember(thread_id=thread.id, user_id=person.id) for person in (sender, recipient)])
            counts['threads'] += 1
        message = Message(thread_id=thread_id, sender_id=sender.id, body='Follow request accepted. You are now connected.')
        session.add(message)
        session.flush()
        session.add(ConnectionRequest(low_id=low, high_id=high, sender_id=sender.id, recipient_id=recipient.id, thread_id=thread_id, message_id=message.id, status='accepted', responded_at=now()))
        counts['connections'] += 1
        counts['messages'] += 1
    session.flush()
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adi-user-id', type=int, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--per-role', type=int, choices=range(1, 11), default=5)
    args = parser.parse_args()
    # Only create the additive new table; do not alter existing accounts or schema.
    ConnectionRequest.__table__.create(engine, checkfirst=True)
    with Session(engine) as session:
        counts = seed(session, args.adi_user_id, args.per_role)
        if args.apply:
            session.commit()
            print('Committed:', counts)
        else:
            session.rollback()
            print('Preview (rolled back):', counts)
