import requests

def test_app_async (launch):
    with launch ("./examples/app_async.py") as engine:
        resp = engine.get ("/")
        assert resp.status_code == 200
        assert resp.text == "Hello Atila"

        resp = engine.get ("/str")
        assert resp.status_code == 200
        assert resp.text == "100"

        resp = engine.get ("/api")
        assert resp.status_code == 200
        assert resp.json ()["x"] == 100
