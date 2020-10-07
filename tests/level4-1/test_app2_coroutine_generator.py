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

        resp = engine.get ('/coroutine_generator?f=1')
        assert resp.status_code == 200
        assert "Example Domain\n" == resp.text

        resp = engine.get ('/coroutine_generator?h=1&f=1')
        assert resp.status_code == 200
        assert "Header Line\nExample Domain\n" == resp.text

        resp = engine.get ('/coroutine_generator?n=100')
        assert resp.status_code == 200
        assert resp.text.count ("Example Domain") == 100

        resp = engine.get ('/coroutine_generator?n=100&h=1')
        assert resp.status_code == 200
        assert resp.text.count ("Example Domain") == 100
        assert resp.text.startswith ("Header Line")
