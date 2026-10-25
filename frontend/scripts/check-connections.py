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
from app.models import User
from app.routers import community, connections, help, home, settings, social, users

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

app = FastAPI()
for router in [connections.router,social.router,users.router,settings.router,community.router,home.router,help.router]:
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
    sender=page_for(ids[0])
    receiver=page_for(ids[1],390)
    sender.goto(f'http://127.0.0.1:5173/u/{ids[1]}')
    sender.get_by_role('button',name='Request to follow',exact=True).click()
    sender.get_by_role('button',name='Requested to follow',exact=True).wait_for()
    link=sender.get_by_role('link',name='View request in messages')
    thread_url=link.get_attribute('href')
    link.click()
    sender.get_by_role('region',name='Conversation',exact=True).get_by_text('Requested to follow.',exact=True).wait_for()
    assert not sender.get_by_role('button',name='Accept follow',exact=True).count()
    receiver.goto('http://127.0.0.1:5173'+thread_url)
    receiver.get_by_role('button',name='Accept follow',exact=True).click()
    receiver.get_by_text('Follow accepted. You are now connected.',exact=True).wait_for()
    sender.get_by_text('Follow accepted. You are now connected.',exact=True).wait_for(timeout=12000)
    sender.reload()
    sender.get_by_text('Follow accepted. You are now connected.',exact=True).wait_for()
    print('Request, delivery, accept, sender polling, and persistence pass.',flush=True)

    # Add the other two roles through the same API so the graph exercises every marker.
    for uid in ids[2:]:
        request=call(ids[0],'POST',f'/connections/users/{uid}')
        call(uid,'POST',f'/connections/requests/{request["id"]}/respond',{'status':'accepted'})
    request=call(ids[2],'POST',f'/connections/users/{ids[3]}')
    call(ids[3],'POST',f'/connections/requests/{request["id"]}/respond',{'status':'accepted'})
    sender.goto('http://127.0.0.1:5173/connections')
    graph=sender.get_by_label('Connections graph with 3 connections.',exact=False)
    graph.wait_for()
    assert graph.locator('a').count()==3
    assert set(graph.locator('a[data-layer]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.layer)'))=={'1','2','3'}
    assert graph.locator('[data-layer-guide]').count()==3
    assert graph.locator('[data-interconnections] line').count()==1
    assert graph.locator('a[data-role="student"] circle').count()==2
    assert graph.locator('a[data-role="mentor"] path').count()==1
    assert graph.locator('a[data-role="faculty"] rect').count()==1
    for person in ['Ashley Student','Morgan Mentor','Devin Faculty','Taylor Student']:
        assert person not in ''.join(graph.locator('text').all_text_contents())
    assert sorted(graph.locator('a title').all_text_contents()) == ['Devin Faculty','Morgan Mentor','Taylor Student']
    def positions():
        return graph.locator('a[data-role]').evaluate_all('(nodes)=>nodes.map(n=>[n.getAttribute("href"),n.querySelector("g").getAttribute("transform")]).sort((a,b)=>a[0].localeCompare(b[0]))')
    initial=positions()
    center=graph.locator('[data-graph-center]').inner_html()
    bounds=graph.bounding_box()
    sender.mouse.move(bounds['x']+bounds['width']/2+45,bounds['y']+bounds['height']/2+20)
    sender.mouse.down()
    sender.mouse.move(bounds['x']+bounds['width']/2+120,bounds['y']+bounds['height']/2+65,steps=12)
    sender.mouse.up()
    assert positions()!=initial
    assert graph.locator('[data-graph-center]').inner_html()==center
    assert sender.url.endswith('/connections')
    graph.focus()
    graph.press('Home')
    assert positions()==initial
    graph.press('ArrowRight')
    assert positions()!=initial
    rotated=positions()
    sender.mouse.wheel(0,-150)
    sender.wait_for_timeout(200)
    assert positions()==rotated
    assert graph.get_attribute('viewBox')=='-210 -210 420 420'
    graph.press('Home')
    sender.evaluate('scrollTo(0,0)')
    sender.screenshot(path=str(out/'desktop.png'),full_page=False)
    print('3D drag and keyboard rotation, fixed center, reset, and no wheel zoom pass.',flush=True)
    sender.emulate_media(reduced_motion='no-preference')
    graph.evaluate('(svg)=>svg.blur()')
    sender.mouse.move(0,0)
    before_spin=positions()
    sender.wait_for_timeout(600)
    assert positions()!=before_spin
    bounds=graph.bounding_box()
    sender.mouse.move(bounds['x']+20,bounds['y']+20)
    paused=positions()
    sender.wait_for_timeout(400)
    assert positions()==paused
    sender.mouse.move(0,0)
    graph.focus()
    paused=positions()
    sender.wait_for_timeout(400)
    assert positions()==paused
    sender.emulate_media(reduced_motion='reduce')
    graph.evaluate('(svg)=>svg.blur()')
    paused=positions()
    sender.wait_for_timeout(400)
    assert positions()==paused
    print('Passive spin, hover/focus pause, and reduced-motion behavior pass.',flush=True)
    receiver.goto('http://127.0.0.1:5173/connections')
    receiver.get_by_role('heading',name='Your connections (1)',exact=True).wait_for()
    receiver.screenshot(path=str(out/'mobile.png'),full_page=False)
    assert receiver.evaluate('document.documentElement.scrollWidth<=innerWidth')
    print('Role markers, nameless graph, accepted lists, and mobile width pass.',flush=True)

    # A separate pair checks denial without modifying an accepted relationship.
    request=call(ids[1],'POST',f'/connections/users/{ids[2]}')
    faculty=page_for(ids[2],320)
    faculty.goto(f'http://127.0.0.1:5173/messages?thread={request["thread_id"]}')
    faculty.get_by_role('button',name='Deny',exact=True).click()
    faculty.get_by_text('You denied this follow request.',exact=True).wait_for()
    receiver.goto(f'http://127.0.0.1:5173/messages?thread={request["thread_id"]}')
    receiver.get_by_text('Your follow request was denied.',exact=True).wait_for()
    assert not faculty.get_by_role('button',name='Accept follow',exact=True).count()
    assert receiver.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert faculty.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    print('Denial and 320px message layout pass. No browser errors.',flush=True)
    print('Screenshots:',out,flush=True)
    browser.close()
client.close()
engine.dispose()
