"""Add fictional sample teams, projects, media posts, logs and comments without overwriting data.
Run: backend/.venv/Scripts/python.exe backend/seed_expanded.py
Safe to rerun: matches sample identities and exact content; one atomic transaction.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import base64
from sqlmodel import Session, select
from app.db import engine
from app.models import User, Project, ProjectMember, LogEntry, Post, Comment, ProfileSettingsRecord

MEDIA=Path(__file__).resolve().parent.parent/'frontend/public/demo-posts'

def student(key,name,major,year,tags):
    return dict(username='sample_'+key,name=name,role='student',major=major,year=year,bio='Fictional sample profile. Learning through small experiments and building with a team.',expertise_tags=tags)
def professional(key,name,role,title,company,tags):
    return dict(username='sample_'+key,name=name,role=role,title=title,company=company,bio='Fictional sample profile. Happy to review project scope, experiments, and technical decisions.',expertise_tags=tags)

PEOPLE=[
    student('naomi','Naomi Brooks','Electrical & Computer Engineering','3rd year',['Python','Arduino','Data Analysis']),
    student('ben','Ben Carter','Computer Science & Engineering','2nd year',['React','TypeScript','SQL']),
    student('amara','Amara Patel','Environmental Engineering','3rd year',['Python','Data Analysis','Arduino']),
    student('lucas','Lucas Nguyen','Computer Science & Engineering','2nd year',['React','FastAPI','PostgreSQL']),
    student('zoe','Zoe Martinez','Electrical & Computer Engineering','4th year',['C++','Embedded Systems','Testing']),
    student('ethan','Ethan Kim','Mechanical Engineering','3rd year',['CAD','Arduino','Python']),
    professional('helen','Dr. Helen Wu','faculty','Faculty advisor, energy systems','Sample University',['Data Analysis','Testing','Python']),
    professional('omar','Dr. Omar Haddad','faculty','Faculty advisor, environmental sensing','Sample University',['System Design','Data Analysis','Testing']),
    professional('sofia','Dr. Sofia Reed','faculty','Faculty advisor, embedded systems','Sample University',['Embedded Systems','Testing','C++']),
    professional('morgan','Morgan Ellis','mentor','Energy Systems Engineer','Northstar Energy Systems (fictional)',['Python','AWS','Data Analysis']),
    professional('devon','Devon Price','mentor','IoT Platform Engineer','Fieldnote AgTech (fictional)',['Arduino','FastAPI','PostgreSQL']),
    professional('riley','Riley Shah','mentor','Embedded Firmware Engineer','CircuitWorks Studio (fictional)',['C++','Embedded Systems','Testing']),
]
TEAMS=[
    dict(slug='solar',title='SolarScope',owner='naomi',members=['naomi','ben','helen','morgan'],status='active',tags=['Python','React','Data Analysis','Arduino'],looking_for=['Data visualization designer','Sensor integration developer'],description='A fictional sample project exploring solar generation monitoring: compare panel output, spot stale readings, and make energy data easier to understand.',
        posts=[('naomi',2,'SolarScope starts with a simple question: can a campus energy display make changing solar output understandable? We mapped the data we need before building the dashboard.','solar-reference.jpg','image','Reference photo: American Public Power Association / Unsplash. This image illustrates the project context, not a team installation.', [('morgan','Good scope. Start by distinguishing a missing reading from a real drop in output.'),('ben','I am adding an explicit last-updated label beside the chart.')]),
               ('ben',6,'First SolarScope dashboard walkthrough: the output trace draws in, panel strings report their status, and the current output stays readable. The clip uses simulated readings.','solar-demo.mp4','video','',[('helen','Keep the units beside every value, and label the simulated feed clearly.'),('naomi','Next step is replaying a saved sensor trace through the same view.')]),
               ('helen',13,'SolarScope review: the team now has a question, a baseline chart, and a test for stale data. This dashboard still is from the sample prototype; no field measurements are claimed.','solar-dashboard.png','image','',[('morgan','I would test a disconnected panel string before adding forecasting.'),('ben','Added that to our failure-case checklist.')]),
               ('morgan',24,'Industry perspective for SolarScope: ship a reliable daily total before chasing prediction accuracy. A small chart with trustworthy timestamps is more useful than a complex chart nobody can explain.',None,None,'',[('naomi','We are keeping forecasting out of this milestone.'),('helen','That tradeoff should make the final evaluation much clearer.')])],
        log=('A readable energy dashboard',['Built an output chart and a panel-status summary.','Added a last-updated indicator.'],['Separated missing measurements from low output.'],['Choosing a useful stale-data threshold.'])),
    dict(slug='greenhouse',title='Greenhouse Watch',owner='amara',members=['amara','lucas','omar','devon'],status='active',tags=['Arduino','FastAPI','React','PostgreSQL'],looking_for=['Embedded systems teammate','UX researcher'],description='A fictional sample project for greenhouse monitoring: bring soil moisture, temperature, and sensor health into a clear dashboard before considering automated watering.',
        posts=[('amara',3,'Greenhouse Watch is our new sensor-to-dashboard build. We are starting with seedlings because moisture changes quickly and labels need to be easy to read at a glance.','greenhouse-reference.jpg','image','Reference photo: Aleksandr Malofeev / Unsplash. A contextual greenhouse photo, not our prototype installation.', [('omar','Write down the sensor placement before comparing moisture readings.'),('lucas','Each reading will carry a sensor ID and timestamp.')]),
               ('lucas',8,'Greenhouse Watch demo: moisture readings stream onto the chart while temperature, humidity, and sensor connectivity stay visible. These are simulated values for the interface prototype.','greenhouse-demo.mp4','video','',[('devon','Make the offline state as clear as the healthy state.'),('amara','We are adding an unplugged-sensor test before any watering rules.')]),
               ('omar',16,'Greenhouse Watch design review: this prototype keeps environmental readings separate from device health. The next experiment is repeatability, not automatic irrigation.','greenhouse-dashboard.png','image','',[('amara','We will log repeated measurements at the same location.'),('devon','Good call. Add calibration notes to the sensor record too.')]),
               ('devon',27,'For Greenhouse Watch, treat every sensor update as a small event: value, unit, timestamp, and sensor identity. That makes the dashboard easier to debug when the network gets unreliable.',None,None,'',[('lucas','The API schema now includes all four fields.'),('omar','Capture a replayable sequence so you can reproduce problems.')])],
        log=('From sensor events to a clear dashboard',['Built a simulated moisture feed.','Connected status cards to a FastAPI prototype.'],['Defined event timestamps and sensor identity.'],['Making disconnected sensors obvious.'])),
    dict(slug='circuit',title='CircuitBench',owner='zoe',members=['zoe','ethan','sofia','riley'],status='archived',tags=['C++','Embedded Systems','Testing','Python'],looking_for=[],description='A completed fictional sample project: a lightweight board-diagnostics interface that checks power, clock, and serial loopback and presents a reproducible test summary.',
        posts=[('zoe',4,'CircuitBench began with the sort of circuit board that turns a loose wire into an afternoon of debugging. Our goal was a repeatable diagnostic checklist, not a universal hardware tester.','circuit-reference.jpg','image','Reference photo: Harrison Broadbent / Unsplash. This circuit-board photo illustrates the domain; it is not the team hardware.', [('riley','A narrow checklist is easier to validate and trust.'),('ethan','We split the fixture notes from the firmware test results.')]),
               ('ethan',10,'CircuitBench final walkthrough: the sample signal trace appears, the checks run, and the summary reports power, clock, and serial loopback. This video uses simulated signals.','circuit-demo.mp4','video','',[('sofia','The pass/fail summary is clear. Keep the raw trace available as evidence.'),('zoe','The project timeline includes our test assumptions and limitations.')]),
               ('sofia',20,'CircuitBench is complete and in the showcase. The important result is a repeatable testing workflow with a small set of explicit checks. This is a still from its diagnostic UI prototype.','circuit-dashboard.png','image','',[('ethan','The fixture assembly notes are included in the final log.'),('riley','Clear boundaries make this a useful portfolio example.')]),
               ('riley',32,'CircuitBench takeaway: a green PASS should mean one specific condition was checked. Label what a test does not establish, especially when people may reuse the fixture on another board.',None,None,'',[('zoe','We added those limitations beside each diagnostic check.'),('sofia','Exactly. Good engineering includes knowing what remains untested.')])],
        log=('Final diagnostic workflow and handoff',['Completed the power, clock, and loopback summary.','Documented fixture assumptions and test limitations.'],['Turned manual checks into a repeatable sequence.'],[])),
]

def media(filename):
    if not filename:return None
    mime='video/mp4' if filename.endswith('.mp4') else 'image/jpeg' if filename.endswith('.jpg') else 'image/png'
    return f'data:{mime};base64,'+base64.b64encode((MEDIA/filename).read_bytes()).decode('ascii')

def seed(session: Session, now: datetime | None=None) -> dict:
    now=now or datetime.now(timezone.utc)
    counts=dict(users=0,projects=0,memberships=0,posts=0,comments=0,logs=0,settings=0)
    people={}
    for fields in PEOPLE:
        username=fields['username'];email=f'{username}@example.invalid'
        user=session.exec(select(User).where(User.username==username)).first()
        if user and (user.email!=email or user.password_hash or user.github_token or user.is_admin):
            raise RuntimeError('A reserved sample username belongs to a non-sample account; no changes committed')
        if not user:
            user=User(**fields,email=email,created_at=now-timedelta(days=22))
            session.add(user);session.flush();counts['users']+=1
        people[username.removeprefix('sample_')]=user
    for offset,team in enumerate(TEAMS):
        owner=people[team['owner']]
        project=session.exec(select(Project).where(Project.owner_id==owner.id,Project.title==team['title'])).first()
        if not project:
            project=Project(owner_id=owner.id,title=team['title'],description=team['description'],tags=team['tags'],looking_for=team['looking_for'],status=team['status'],start_date=(now-timedelta(days=21)).date().isoformat(),end_date=now.date().isoformat() if team['status']=='archived' else (now+timedelta(days=21)).date().isoformat(),created_at=now-timedelta(days=21))
            session.add(project);session.flush();counts['projects']+=1
        for key in team['members']:
            member=people[key]
            if not session.get(ProjectMember,(project.id,member.id)):
                session.add(ProjectMember(project_id=project.id,user_id=member.id,role='owner' if member.id==owner.id else 'member'));counts['memberships']+=1
            if not session.get(ProfileSettingsRecord,member.id):
                session.add(ProfileSettingsRecord(user_id=member.id,data={'availability':'teammates' if member.role=='student' else 'available_to_mentor','interests':[team['title']],'hours_per_week':4}));counts['settings']+=1
        session.flush()
        for author,hours,body,filename,kind,credit,comments in team['posts']:
            content='[Sample project] '+body+(('\n\n'+credit) if credit else '')
            post=session.exec(select(Post).where(Post.author_id==people[author].id,Post.project_id==project.id,Post.body==content)).first()
            if not post:
                post=Post(author_id=people[author].id,project_id=project.id,body=content,media_url=media(filename),media_kind=kind,created_at=now-timedelta(hours=hours,minutes=offset*11))
                session.add(post);session.flush();counts['posts']+=1
            for i,(commenter,comment) in enumerate(comments):
                exists=session.exec(select(Comment).where(Comment.post_id==post.id,Comment.author_id==people[commenter].id,Comment.body==comment)).first()
                if not exists:
                    session.add(Comment(post_id=post.id,author_id=people[commenter].id,body=comment,created_at=post.created_at+timedelta(minutes=15+i*12)));counts['comments']+=1
        title,built,learned,stuck=team['log']
        log=session.exec(select(LogEntry).where(LogEntry.project_id==project.id,LogEntry.author_id==owner.id,LogEntry.title==title)).first()
        if not log:
            log=LogEntry(project_id=project.id,author_id=owner.id,title=title,week_label='Sample project / final update' if team['status']=='archived' else 'Sample project / week 1',built=built,learned=learned,stuck=stuck,skills=team['tags'],source='manual',created_at=now-timedelta(hours=36+offset))
            session.add(log);session.flush();counts['logs']+=1
        if not session.exec(select(Post).where(Post.log_entry_id==log.id)).first():
            session.add(Post(author_id=owner.id,project_id=project.id,log_entry_id=log.id,body=title,type='log',created_at=log.created_at));counts['posts']+=1
    session.flush()
    return counts

if __name__=='__main__':
    with Session(engine) as session:
        with session.begin():
            counts=seed(session)
        print(counts)
