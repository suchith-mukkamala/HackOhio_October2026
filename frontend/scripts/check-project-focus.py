"""Mocked browser checks for the project-completion home experience.
Start Vite on port 5173. Requires Playwright and an installed Edge browser.
"""
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    for width, role, state in [(1280,'student','active'),(390,'student','active'),(320,'student','empty'),(390,'mentor','active'),(1280,'faculty','empty'),(390,'student','error')]:
        page = browser.new_page(viewport={'width':width,'height':740}, reduced_motion='reduce')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        user = dict(id=999,name='Taylor Morgan',role=role,major='Computer Science',expertise_tags=[],is_admin=False)
        project = dict(id=123,owner_id=999,title='Campus Room Finder',description='A working room finder.',tags=['React'],looking_for=['Designer'],status='active',end_date='2026-11-15')
        sidebar = dict(my_projects=[] if state=='empty' else [dict(project=project,latest_log_title='Working prototype',last_activity_at='2026-10-24T17:00:00Z',needs_log=True)],active_project_count=0 if state=='empty' else 1,opportunities=[])
        def route_api(route):
            path=urlparse(route.request.url).path
            if path=='/api/home/sidebar' and state=='error':
                route.fulfill(status=500,json={'detail':'Test failure'}); return
            route.fulfill(json={'/api/me':user,'/api/home/sidebar':sidebar}.get(path,[]))
        page.route('**/api/**',route_api)
        page.goto('http://127.0.0.1:5173/feed')
        focus=page.get_by_role('region',name='Move your project forward' if role=='student' else 'Help a team finish')
        focus.wait_for()
        if state=='active':
            focus.get_by_role('link',name='Campus Room Finder',exact=True).wait_for()
            assert focus.get_by_text('Target finish:',exact=False).first.is_visible()
            next_step=focus.get_by_role('link',name='Share progress' if role=='student' else 'Review progress')
            assert next_step.get_attribute('href')==('/projects/123?write=1' if role=='student' else '/projects/123')
        elif state=='empty':
            focus.get_by_text('Join a team or start a small project.' if role=='student' else 'Find a team to support.').wait_for()
            assert focus.get_by_role('link',name='Find a project to join' if role=='student' else 'Explore teams').get_attribute('href')=='/explore?category=projects'
        else:
            focus.get_by_role('alert').wait_for()
            assert focus.get_by_role('button',name='Try again').is_visible()
            assert not focus.get_by_text('Join a team or start a small project.').count()
        assert focus.bounding_box()['height'] < 230
        composer=page.get_by_role('textbox',name='Share project progress').bounding_box()
        assert composer['y']+composer['height'] < 740, composer
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not page.get_by_text('// your ladder',exact=True).count()
        page.goto('http://127.0.0.1:5173/explore')
        page.get_by_role('button',name='Projects',exact=False).first.wait_for()
        assert page.get_by_role('button',name='Projects',exact=False).first.get_attribute('aria-pressed')=='true'
        page.get_by_role('button',name='Teammates',exact=False).click()
        assert 'category=students' in page.url
        page.reload()
        assert page.get_by_role('button',name='Teammates',exact=False).get_attribute('aria-pressed')=='true'
        assert not errors, errors
        print(dict(width=width,role=role,state=state,errors=errors),flush=True)
        page.close()
    browser.close()
