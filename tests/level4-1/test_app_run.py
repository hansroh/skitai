import requests

def test_app_run (launch):
    with launch ("./examples/appatila.py") as engine:
        resp = requests.get ('http://localhost:30371/')
        assert resp.status_code == 200
        resp = requests.get ('http://localhost:30371/statics/reindeer.jpg')
        assert resp.status_code == 200



