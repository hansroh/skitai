import requests
import platform

def test_app (launch):
    with launch ("./examples/app2.py") as engine:
        resp = engine.get ('/reindeer')
        assert resp.headers.get ('etag')
        assert resp.headers.get ('content-type') == 'image/jpeg'
        assert resp.headers.get ('content-length') == '32772'

        resp = engine.get ('/file')
        assert resp.headers.get ('content-type') == 'application/octet-stream'
        assert resp.headers.get ('content-length') == '32772'
