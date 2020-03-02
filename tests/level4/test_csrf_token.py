import requests

def test_app (launch):
    with launch ("./examples/app2.py") as engine:
        resp = engine.get ('/')
        assert resp.status_code == 200
        csrf = resp.text [5:].strip ()

        resp = engine.post ('/post', {'a': 'b'})
        assert resp.status_code == 400

        resp = engine.post ('/post', {'_csrf_token': csrf, 'a': 'b'})
        assert resp.status_code == 200
        assert resp.text == 'OK'

        resp = engine.get ('/')
        assert resp.status_code == 200
        csrf = resp.text [5:].strip ()

        resp = engine.post ('/post', {'_csrf_token': csrf, 'a': 'b'}, headers = {'X-CSRF-Token': csrf})
        assert resp.status_code == 200
        assert resp.text == 'OK'

