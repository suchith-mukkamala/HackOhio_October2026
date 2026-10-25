"""Mocked profile graph entrance QA. Requires Vite on 5173, Playwright and Edge."""
from urllib.parse import urlparse
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright

user = dict(id=999,name='Graph Tester',role='student',expertise_tags=[],is_admin=False)
nodes = [dict(skill=skill,parent=parent,tier=tier,pulse=.5,score=1,evidence=[]) for skill,parent,tier in [('Programming',None,'category'),('Web','Programming','derived'),('React','Web','claimed'),('TypeScript','Web','claimed'),('Design',None,'category')]]
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge',headless=True)
    for width,system_reduce,setting_reduce in [(1280,False,False),(390,False,False),(390,True,False),(1280,False,True)]:
        page = browser.new_page(viewport=dict(width=width,height=900),reduced_motion='reduce' if system_reduce else 'no-preference')
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        fixtures={'/api/me':user,'/api/users/999':dict(user=user,projects=[],endorsements=[],experience=[]),'/api/users/999/skills':dict(nodes=nodes,edges=[dict(a='React',b='TypeScript',weight=1)]),'/api/me/settings':dict(preferences=dict(reduce_motion=setting_reduce,particles=True)),'/api/skills/vocabulary':dict(categories=[],skills=[]),'/api/connections':dict(connections=[],requests=[],interconnections=[])}
        page.route('**/api/**',lambda route:route.fulfill(json=fixtures.get(urlparse(route.request.url).path,[])))
        page.goto('http://127.0.0.1:5173/u/999')
        graph=page.locator('.skillgraph')
        graph.wait_for()
        assert graph.locator('.sg-node').count()==len(nodes)
        if system_reduce or setting_reduce:
            page.wait_for_function("document.querySelector('.skillgraph').dataset.growth === '1.0000'")
            assert graph.locator('.sg-flow').first.evaluate('(n)=>getComputedStyle(n).display')=='none'
        else:
            def snapshot():
                return graph.evaluate('(g)=>({growth:Number(g.dataset.growth),points:[...g.querySelectorAll(".sg-dot")].map(n=>[Number(n.getAttribute("cx")),Number(n.getAttribute("cy"))])})')
            first=snapshot()
            assert first['growth'] < .7
            page.wait_for_timeout(800)
            second=snapshot()
            page.wait_for_timeout(800)
            third=snapshot()
            assert first['growth'] < second['growth'] < third['growth'] < 1
            assert third['growth']-second['growth'] > second['growth']-first['growth'], 'The entrance should gently accelerate before its steady middle'
            assert graph.locator('.sg-flow').first.evaluate('(n)=>getComputedStyle(n).visibility')=='visible'
            for color in ['blue','yellow']:
                assert graph.locator('.sg-flow-'+color).evaluate_all('(nodes)=>nodes.some(n=>getComputedStyle(n).display!=="none" && Number(getComputedStyle(n).opacity)>0)')
            page.wait_for_function("Number(document.querySelector('.skillgraph').dataset.growth) > .9")
            end_first=snapshot()['growth']
            page.wait_for_timeout(200)
            end_second=snapshot()['growth']
            page.wait_for_timeout(200)
            end_third=snapshot()['growth']
            assert end_third-end_second <= end_second-end_first+.005, 'The expansion should gently decelerate at the end'
            page.wait_for_function("document.querySelector('.skillgraph').dataset.growth === '1.0000'")
            final=snapshot()
            for early,finished in zip(second['points'],final['points']):
                for axis in [0,1]:
                    assert abs(early[axis]-(400+(finished[axis]-400)*second['growth'])) < .1
            if width == 1280:
                graph.screenshot(path=str(Path(tempfile.gettempdir())/'keystone-skill-entrance.png'))
        graph.get_by_role('button',name='Programming, category',exact=True).locator('.sg-dot').click(timeout=5000)
        assert graph.locator('.sg-node').count()==len(nodes)
        assert graph.locator('.sg-panel').get_by_role('heading',name='Programming',exact=True).is_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors,errors
        print(dict(width=width,system_reduce=system_reduce,setting_reduce=setting_reduce,all_nodes_extended=True,errors=errors),flush=True)
        page.close()
    browser.close()
