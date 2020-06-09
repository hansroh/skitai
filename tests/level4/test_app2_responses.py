import requests
import platform

def test_app (launch):
    with launch ("./examples/app2.py") as engine:
        resp = engine.get ('/map_in_thread')
        assert resp.status_code == 200
        assert resp.data == {'media': 'Hello'}

        resp = engine.get ('/reindeer')
        assert resp.headers.get ('etag')
        assert resp.headers.get ('content-type') == 'image/jpeg'
        assert resp.headers.get ('content-length') == '32772'

        resp = engine.get ('/file')
        assert resp.headers.get ('content-type') == 'application/octet-stream'
        assert resp.headers.get ('content-length') == '32772'

        resp = engine.get ('/stream')
        assert resp.status_code == 210
        assert resp.headers.get ('content-type') == 'text/plain'
        assert resp.data.count (b'<CHUNK>') == 100

        resp = engine.get ('/thread_future')
        assert resp.status_code == 200
        assert resp.data == b'Hello'
