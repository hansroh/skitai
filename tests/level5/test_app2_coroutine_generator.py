import requests
import platform

def test_app (launch):
    with launch ("./examples/app2.py") as engine:
        resp = engine.get ('/coroutine/2')
        assert resp.status_code == 200
        assert "pypi" in resp.text

        resp = engine.get ('/coroutine_generator?n=1')
        assert resp.status_code == 200
        assert "pypi" in resp.text

        resp = engine.get ('/coroutine_generator?f=1')
        assert resp.status_code == 200
        assert "pypi" in resp.text

        resp = engine.get ('/coroutine_generator?h=1&f=1')
        assert resp.status_code == 200
        assert "Header Line\npypi" in resp.text

        resp = engine.get ('/coroutine_generator?n=100')
        assert resp.status_code == 200
        assert resp.text.count ("pypi") == 100

        resp = engine.get ('/coroutine_generator?n=100&h=1')
        assert resp.status_code == 200
        assert resp.text.count ("pypi") == 100
        assert resp.text.startswith ("Header Line")
