import requests
from pprint import pprint

def test_selective (launch):
    with launch ("./examples/app2.py") as engine:
        for i in range (10):
            resp = engine.get ('/render_or_API')
            assert 'text/html' in resp.headers ['content-type']
            resp = engine.get ('/render_or_API', headers = {'Accept': 'application/json, text/html'})
            assert 'application/json' in resp.headers ['content-type']
            resp = engine.get ('/render_or_API', headers = {'Accept': 'application/json, */*'})
            assert 'application/json' in resp.headers ['content-type']
            resp = engine.get ('/render_or_API', headers = {'Accept': 'text/html'})
            assert 'text/html' in resp.headers ['content-type']
            resp = engine.get ('/render_or_API', headers = {'Accept': 'text/plain'})
            assert 'text/html' in resp.headers ['content-type']

        for i in range (10):
            resp = engine.get ('/render_or_Map')
            assert 'text/html' in resp.headers ['content-type']
            resp = engine.get ('/render_or_Map', headers = {'Accept': 'application/json, */*'})
            assert 'application/json' in resp.headers ['content-type']
            resp = engine.get ('/render_or_Map', headers = {'Accept': 'text/html'})
            assert 'text/html' in resp.headers ['content-type']
            resp = engine.get ('/render_or_Map', headers = {'Accept': 'text/plain'})
            assert 'text/html' in resp.headers ['content-type']

        for i in range (10):
            resp = engine.get ('/render_or_Mapped')
            assert 'text/html' in resp.headers ['content-type']
            resp = engine.get ('/render_or_Mapped', headers = {'Accept': 'application/json'})
            assert 'application/json' in resp.headers ['content-type']
            resp = engine.get ('/render_or_Mapped', headers = {'Accept': 'text/html, */*'})
            assert 'text/html' in resp.headers ['content-type']
            resp = engine.get ('/render_or_Mapped', headers = {'Accept': 'text/plain'})
            assert 'text/html' in resp.headers ['content-type']
