"""Browser QA backed by an isolated in-memory API, never the configured database.
Start Vite on port 5173; run with the backend venv (Playwright + Edge required).
"""
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['JWT_SECRET'] = 'isolated-test-signing-key-at-least-32-bytes'
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from playwright.sync_api import sync_playwright
from app.auth import current_user, optional_user
from app.db import get_session
from app.models import User, Project, ProjectMember, Post
from app.routers import community, connections, help, home, settings, social, users, projects, invitations, admin

engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
SQLModel.metadata.create_all(engine)
with Session(engine) as session:
    people = [User(name=name,role=role,expertise_tags=[]) for name,role in [('Ashley Student','student'),('Morgan Mentor','mentor'),('Devin Faculty','faculty'),('Taylor Student','student')]]
    session.add_all(people)
    session.commit()
    ids = []
    for person in people:
        session.refresh(person)
        ids.append(person.id)

with Session(engine) as session:
    project=Project(owner_id=ids[0],title='Ship a room finder',description='A small finished demo.')
    session.add(project)
    session.commit()
    session.refresh(project)
    pid=project.id
    session.add(ProjectMember(project_id=pid,user_id=ids[0],role='owner'))
    session.commit()
with Session(engine) as session:
    account=session.get(User,ids[0])
    account.is_admin=True
    account.username='adi'
    target=session.get(User,ids[1])
    target.username='target-account'
    session.add_all([account,target])
    owned=Project(owner_id=ids[1],title='Target owned project')
    session.add(owned)
    session.flush()
    session.add(Post(author_id=ids[1],project_id=owned.id,body='Target post'))
    session.commit()
app = FastAPI()
for router in [connections.router,social.router,users.router,settings.router,community.router,home.router,help.router,projects.router,invitations.router,admin.router]:
    app.include_router(router,prefix='/api')
def session_dependency():
    with Session(engine) as session:
        yield session
def actor(request: Request, session: Session = Depends(get_session)):
    return session.get(User,int(request.headers['x-qa-user']))
app.dependency_overrides[get_session] = session_dependency
app.dependency_overrides[current_user] = actor
app.dependency_overrides[optional_user] = actor
client = TestClient(app)
out = Path(tempfile.gettempdir())/'keystone-connections-qa'
out.mkdir(exist_ok=True)

def call(actor_id,method,path,body=None):
    response = client.request(method,'/api'+path,headers={'x-qa-user':str(actor_id)},json=body)
    assert response.status_code==200,response.text
    return response.json()

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge',headless=True)
    errors=[]
    def page_for(uid,width=1280):
        page=browser.new_page(viewport={'width':width,'height':900},reduced_motion='reduce')
        page.on('pageerror',lambda error: errors.append(str(error)))
        def route_api(route):
            parsed=urlparse(route.request.url)
            response=client.request(route.request.method,parsed.path+('?' + parsed.query if parsed.query else ''),headers={'x-qa-user':str(uid),'content-type':'application/json'},content=route.request.post_data)
            route.fulfill(status=response.status_code,body=response.content,content_type='application/json')
        page.route('**/api/**',route_api)
        return page
    page=page_for(ids[0])
    page.goto('http://127.0.0.1:5173/admin')
    page.get_by_role('searchbox',name='Search users').fill('target-account')
    page.get_by_role('button',name=f'Delete Morgan Mentor, user {ids[1]}',exact=True).click()
    dialog=page.get_by_role('dialog',name='Delete Morgan Mentor?',exact=True)
    dialog.get_by_text('Target owned project',exact=True).wait_for()
    assert len(call(ids[0],'GET','/admin/users'))==4
    assert dialog.get_by_role('button',name='Permanently delete user').is_disabled()
    dialog.get_by_role('textbox').fill('DELETE wrong-user')
    assert dialog.get_by_role('button',name='Permanently delete user').is_disabled()
    dialog.press('Escape')
    assert not page.get_by_role('dialog').count()
    page.get_by_role('button',name=f'Delete Morgan Mentor, user {ids[1]}',exact=True).click()
    dialog=page.get_by_role('dialog')
    dialog.get_by_text('Target owned project',exact=True).wait_for()
    dialog.get_by_role('textbox').fill(f'DELETE {ids[1]}')
    dialog.get_by_role('button',name='Permanently delete user',exact=True).click()
    page.get_by_text(f'Deleted Morgan Mentor (user {ids[1]}) and associated data.',exact=True).wait_for()
    assert len(call(ids[0],'GET','/admin/users'))==3
    assert call(ids[0],'GET',f'/projects/{pid}')['project']['title']=='Ship a room finder'
    page.set_viewport_size(dict(width=320,height=800))
    page.get_by_role('searchbox',name='Search users').fill('Devin')
    page.get_by_role('button',name=f'Delete Devin Faculty, user {ids[2]}',exact=True).click()
    dialog=page.get_by_role('dialog')
    dialog.get_by_text('Records to remove',exact=True).wait_for()
    box=dialog.bounding_box()
    assert box['x']>=0 and box['x']+box['width']<=320,box
    assert box['height']<=680,box
    dialog.get_by_role('button',name='Cancel',exact=True).click()
    assert len(call(ids[0],'GET','/admin/users'))==3
    outsider=page_for(ids[2],390)
    outsider.goto('http://127.0.0.1:5173/admin')
    outsider.get_by_role('heading',name='Admin access',exact=True).wait_for()
    assert not outsider.get_by_role('button',name='Permanently delete user').count()
    assert not errors,errors
    print('Read-only preview, exact-ID confirmation, Escape/cancel, deletion, unrelated-project preservation, mobile dialog, and non-admin UI pass.',flush=True)
    browser.close()
client.close()
engine.dispose()