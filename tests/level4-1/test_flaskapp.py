import pytest

def test_flask (launch):
    with launch ("./examples/flaskapp.py") as engine:
        resp = engine.get ("/3")
        assert resp.status_code == 200
        assert "hello, flask" == resp.text


def test_flask_async_enabled (launch):
    with launch ("./examples/flaskapp_async.py") as engine:
        resp = engine.get ("/3")
        assert resp.status_code == 200
        assert "hello, flask" == resp.text
