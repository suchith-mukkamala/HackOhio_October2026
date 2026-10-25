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
from app.models import User, Project, ProjectMember
from app.routers import community, connections, help, home, settings, social, users, projects, invitations

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
app = FastAPI()
for router in [connections.router,social.router,users.router,settings.router,community.router,home.router,help.router,projects.router,invitations.router]:
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
    owner=page_for(ids[0])
    recipient=page_for(ids[1],390)
    outsider=page_for(ids[2],320)
    owner.goto(f'http://127.0.0.1:5173/projects/{pid}')
    owner.get_by_role('button',name='Invite people',exact=True).click()
    panel=owner.get_by_role('region',name='Invite people to project',exact=True)
    panel.get_by_role('searchbox',name='Find people to invite').fill('Morgan')
    panel.get_by_role('button',name='Invite Morgan Mentor',exact=True).click()
    panel.get_by_text('Invitation sent.',exact=True).wait_for()
    assert panel.get_by_role('button',name='Invite Morgan Mentor',exact=True).is_disabled()
    recipient.goto('http://127.0.0.1:5173/messages')
    inbox=recipient.get_by_role('region',name='Project invitations',exact=True)
    inbox.get_by_role('button',name='Accept invitation',exact=True).click()
    inbox.get_by_text('You joined Ship a room finder.',exact=False).wait_for()
    recipient.goto(f'http://127.0.0.1:5173/projects/{pid}')
    recipient.get_by_role('button',name='Edit project',exact=True).wait_for()
    assert recipient.get_by_role('button',name='Invite people',exact=True).is_visible()
    assert recipient.evaluate('document.documentElement.scrollWidth<=innerWidth')
    panel.get_by_role('searchbox',name='Find people to invite').fill('Devin')
    panel.get_by_role('button',name='Invite Devin Faculty',exact=True).click()
    panel.get_by_text('Invitation sent.',exact=True).wait_for()
    outsider.goto(f'http://127.0.0.1:5173/projects/{pid}')
    assert not outsider.get_by_role('button',name='Invite people',exact=True).count()
    incoming=outsider.get_by_role('region',name='Project invitations',exact=True)
    incoming.get_by_role('button',name='Decline',exact=True).click()
    incoming.get_by_text('Invitation to Ship a room finder declined.',exact=False).wait_for()
    assert not outsider.get_by_role('button',name='Edit project',exact=True).count()
    panel.locator('summary').click()
    panel.get_by_text('declined',exact=True).wait_for(timeout=10000)
    assert outsider.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    print('Invite search, delivery, acceptance, team permissions, decline, sender status, and mobile layout pass.',flush=True)
    browser.close()
client.close()
engine.dispose()