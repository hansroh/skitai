import requests

def test_app_run (launch):
    with launch ("./examples/app_extends.py") as engine:
        resp = requests.get ('http://localhost:30371/')
        assert resp.status_code == 200
        assert resp.text == "Hello Atila"

        resp = requests.get ('http://localhost:30371/statics/reindeer.jpg')
        assert resp.status_code == 200

        resp = requests.get ('http://localhost:30371/statics/manifest.json')
        assert resp.status_code == 200

        resp = requests.get ('http://localhost:30371/statics/vue2/_framework/supplement.css')
        assert resp.status_code == 200


