import pytest
import requests
import time
def test_reload (launch):
    with launch ("./examples/app.py") as engine:
        resp = requests.get ("http://127.0.0.1:30371/response_chain")
        assert resp.status_code == 200

