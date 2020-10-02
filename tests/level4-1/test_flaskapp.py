import pytest

def test_launch (launch):
    with launch ("./examples/flaskapp.py") as engine:
        resp = engine.get ("/")
        assert "Project description" in resp.text

        resp = engine.get ("/2")
        assert resp.status_code == 500




