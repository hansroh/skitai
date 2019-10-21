import requests

def test_app (launch):
    with launch ("./examples/https_forward.py") as engine:
        resp = requests.get ('http://localhost:12443/a?b=c', verify = False, timeout = 5)
        assert resp.history [0].status_code == 301
        assert resp.history [1].status_code == 301
        assert resp.history [1].headers ["location"] == "https://127.0.0.1:30371/a?b=c"
        assert resp.status_code == 404



