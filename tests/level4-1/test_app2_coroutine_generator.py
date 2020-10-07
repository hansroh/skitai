import requests
import platform

def test_app (launch):
    with launch ("./examples/app2.py") as engine:
        resp = engine.get ('/coroutine/2')
        assert resp.status_code == 200
        assert "Example Domain" in resp.text

        resp = engine.get ('/coroutine_generator?n=1')
        assert resp.status_code == 200
        assert "Example Domain" == resp.text

        resp = engine.get ('/coroutine_generator?n=100')
        assert resp.status_code == 200
        assert resp.text.count ("Example Domain") == 100
