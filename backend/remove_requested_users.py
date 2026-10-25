"""Remove the explicitly requested jjjj / Full name accounts and dependent data.
Preview rolls back. --apply commits one transaction after validating exact identities.
"""
import argparse
from sqlmodel import Session
from app.db import engine
from app.models import User
from app.services.user_cleanup import cleanup

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids', type=int, nargs='+', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with Session(engine) as session:
        selected = [session.get(User, uid) for uid in set(args.ids)]
        labels = {'jjjj', 'full name'}
        if len(selected) != 2 or any(user is None or not ({(user.username or '').strip().lower(), user.name.strip().lower()} & labels) for user in selected):
            raise RuntimeError('Exact requested identities could not be verified; no changes committed')
        print('Accounts:', [dict(id=user.id, username=user.username, name=user.name) for user in selected], flush=True)
        result = cleanup(session, set(args.ids))
        if args.apply:
            session.commit()
            print('Committed:', result)
        else:
            session.rollback()
            print('Preview (rolled back):', result)
