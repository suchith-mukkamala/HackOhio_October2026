"""Dependency-aware account removal shared by admin tools and maintenance scripts."""
from copy import deepcopy
from sqlalchemy import or_
from sqlmodel import Session, select
from ..models import (User, Project, ProjectMember, Invite, LogEntry, Post, Comment,
    HelpRequest, Endorsement, Thread, ThreadMember, Message, ConnectionRequest,
    Experience, ProfileSettingsRecord, ClubMember, Challenge)

def cleanup(session: Session, user_ids: set[int], preview: bool = False):
    def ids(model, condition):
        return set(session.exec(select(model.id).where(condition)).all())
    projects = ids(Project, Project.owner_id.in_(user_ids))
    logs = ids(LogEntry, or_(LogEntry.author_id.in_(user_ids), LogEntry.project_id.in_(projects)))
    help_ids = ids(HelpRequest, or_(HelpRequest.requester_id.in_(user_ids), HelpRequest.project_id.in_(projects)))
    challenges = session.exec(select(Challenge).where(Challenge.user_id.in_(user_ids))).all()
    challenge_posts = {row.post_id for row in challenges if row.post_id is not None}
    posts = ids(Post, or_(Post.author_id.in_(user_ids), Post.project_id.in_(projects), Post.log_entry_id.in_(logs), Post.id.in_(challenge_posts)))
    memberships = session.exec(select(ThreadMember)).all()
    members_by_thread = {}
    for member in memberships:
        members_by_thread.setdefault(member.thread_id, set()).add(member.user_id)
    threads = {tid for tid, members in members_by_thread.items() if members and members <= user_ids}
    messages = ids(Message, or_(Message.sender_id.in_(user_ids), Message.thread_id.in_(threads)))
    requests = session.exec(select(ConnectionRequest).where(or_(ConnectionRequest.low_id.in_(user_ids), ConnectionRequest.high_id.in_(user_ids), ConnectionRequest.sender_id.in_(user_ids), ConnectionRequest.recipient_id.in_(user_ids), ConnectionRequest.thread_id.in_(threads), ConnectionRequest.message_id.in_(messages)))).all()
    messages.update(row.message_id for row in requests)
    deleted = {}
    updated = {}
    def remove(model, condition):
        rows = session.exec(select(model).where(condition)).all()
        deleted[model.__tablename__] = len(rows)
        if preview:
            return
        for row in rows:
            session.delete(row)
        session.flush()
    # Preserve other people's questions and challenge entries, clearing deleted users' work.
    for row in session.exec(select(HelpRequest).where(HelpRequest.mentor_id.in_(user_ids), HelpRequest.id.not_in(help_ids))).all():
        if not preview:
            row.mentor_id, row.answer, row.helpful, row.status = None, None, None, 'open'
            session.add(row)
        updated['help_answers_cleared'] = updated.get('help_answers_cleared', 0) + 1
    for row in session.exec(select(Challenge).where(Challenge.user_id.not_in(user_ids))).all():
        changed = False
        if row.judge_id in user_ids:
            if not preview:
                row.judge_id, row.score, row.feedback = None, None, ''
            changed = True
        if row.post_id in posts:
            if not preview:
                row.post_id = None
            changed = True
        if changed:
            if not preview:
                session.add(row)
            updated['challenges_preserved'] = updated.get('challenges_preserved', 0) + 1
    for row in session.exec(select(ProfileSettingsRecord).where(ProfileSettingsRecord.user_id.not_in(user_ids))).all():
        data = deepcopy(row.data)
        if 'pinned_project_ids' in data:
            data['pinned_project_ids'] = [pid for pid in data['pinned_project_ids'] if pid not in projects]
        if data.get('pinned_post_id') in posts:
            data['pinned_post_id'] = None
        if data != row.data:
            if not preview:
                row.data = data
                session.add(row)
            updated['pins_cleared'] = updated.get('pins_cleared', 0) + 1
    if not preview:
        session.flush()
    remove(ConnectionRequest, ConnectionRequest.id.in_([row.id for row in requests]))
    remove(Message, Message.id.in_(messages))
    remove(ThreadMember, or_(ThreadMember.user_id.in_(user_ids), ThreadMember.thread_id.in_(threads)))
    remove(Thread, Thread.id.in_(threads))
    remove(Endorsement, or_(Endorsement.from_id.in_(user_ids), Endorsement.to_id.in_(user_ids), Endorsement.project_id.in_(projects), Endorsement.help_request_id.in_(help_ids)))
    remove(Comment, or_(Comment.author_id.in_(user_ids), Comment.project_id.in_(projects), Comment.post_id.in_(posts)))
    remove(Challenge, Challenge.user_id.in_(user_ids))
    remove(Post, Post.id.in_(posts))
    remove(LogEntry, LogEntry.id.in_(logs))
    remove(HelpRequest, HelpRequest.id.in_(help_ids))
    remove(Invite, or_(Invite.from_id.in_(user_ids), Invite.to_id.in_(user_ids), Invite.project_id.in_(projects)))
    remove(ProjectMember, or_(ProjectMember.user_id.in_(user_ids), ProjectMember.project_id.in_(projects)))
    remove(Project, Project.id.in_(projects))
    remove(Experience, Experience.user_id.in_(user_ids))
    remove(ProfileSettingsRecord, ProfileSettingsRecord.user_id.in_(user_ids))
    remove(ClubMember, ClubMember.user_id.in_(user_ids))
    remove(User, User.id.in_(user_ids))
    return dict(deleted=deleted, updated=updated)


