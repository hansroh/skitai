import requests

def test_app (launch):
    with launch ("./examples/app2.py") as engine:
        resp = engine.get ('/render_or_API', headers = {'Accept': 'application/json, */*'})
        assert 'application/json' in resp.headers ['content-type']
        resp = engine.get ('/render_or_API', headers = {'Accept': 'text/html, */*'})
        assert 'text/html' in resp.headers ['content-type']
        resp = engine.get ('/render_or_API', headers = {'Accept': 'text/plain, */*'})
        assert 'text/html' in resp.headers ['content-type'] or 'application/json' in resp.headers ['content-type']
