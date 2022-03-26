import requests

def test_app_run (launch):
    with launch ("./examples/asyncapp.py") as engine:
        return
        resp = requests.get ('http://localhost:30371/')
        assert resp.status_code == 200
