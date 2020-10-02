import pytest
import requests
import time
def test_reload (launch):
    with launch ("./examples/app.py") as engine:
        resp = engine.get ("/response_chain")
        assert resp.status_code == 200

        resp = engine.get ("/mixing")
        assert resp.status_code == 200
        assert 'a' in resp.data
        assert 'b' in resp.data
        assert 'c' in resp.data

        assert 'rs4' in resp.data ['b']
        assert resp.data ['c'] == None
        assert isinstance (resp.data ['a'], list)
        assert '.py' in resp.data ['f']


