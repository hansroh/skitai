import pytest

def test_launch (launch):
    with launch ("./examples/flaskapp.py") as engine:
        resp = engine.get ("/")
        assert resp.status_code == 500
        assert "Project description" not in resp.text

        resp = engine.get ("/2")
        assert resp.status_code == 500

        resp = engine.get ("/3")
        assert resp.status_code == 200
        assert "hello, flask" == resp.text



