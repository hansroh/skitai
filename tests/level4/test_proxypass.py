import pytest
import requests

def test_proxy (launch):
    with launch ("./examples/reverse_proxy.py") as engine:
        resp = requests.get ("http://127.0.0.1:30371/lb2/rs4/")
        assert resp.status_code == 200
        assert "Project description" in resp.text

        resp = requests.get ("http://127.0.0.1:30371/lb/project/rs4/")
        assert resp.status_code == 200
        assert "Project description" in resp.text

def test_https (launch):
    with launch ("./examples/reverse_proxy.py") as engine:
        resp = requests.get ("http://127.0.0.1:30371/pypi")
        assert resp.status_code == 200
        assert "Project description" in resp.text

