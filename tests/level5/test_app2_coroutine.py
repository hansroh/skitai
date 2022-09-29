import requests
import platform

def test_app (launch):
    with launch ("./examples/app2.py") as engine:
        # resp = engine.get ('/coroutine')
        # assert resp.status_code == 200
        # assert "pypi" in resp.text

        # resp = engine.get ('/coroutine/2')
        # assert resp.status_code == 200
        # assert "pypi" in resp.text

        # resp = engine.get ('/coroutine/3')
        # assert resp.status_code == 200
        # assert "pypi" in resp.text

        resp = engine.axios.get ('/coroutine/4')
        assert resp.status_code == 200
        assert "pypi" in resp.text
        assert resp.data ['b'] == 'mask'

        resp = engine.axios.get ('/coroutine/5')
        assert resp.status_code == 200
        assert "pypi" in resp.text
        assert resp.data ['b'] == 'mask'

        resp = engine.axios.get ('/coroutine/6')
        assert resp.status_code == 200
        assert "pypi" in resp.text
        assert resp.data ['b'] == 'mask'

        resp = engine.axios.get ('/coroutine/7')
        assert resp.status_code == 200
        assert "pypi" in resp.text
        assert resp.data ['b'] == 'mask'

        resp = engine.axios.get ('/coroutine/8')
        assert resp.status_code == 200
        assert "pypi" in resp.text
        assert resp.data ['b'] == 'mask'
        assert resp.data ['c'] == 100

        resp = engine.axios.get ('/coroutine/9')
        assert resp.status_code == 200
        assert "pypi" in resp.text
        assert resp.data ['b'] == 'mask'
        assert resp.data ['c'] == 'mask'
        assert 'app.py' in resp.data ['d']

        resp = engine.axios.get ('/coroutine/10')
        assert resp.status_code == 200
        assert "pypi" in resp.text
        assert resp.data ['b'] == 'mask'
        assert resp.data ['c'] == 'mask'
        assert 'app.py' in resp.data ['d']

        resp = engine.axios.get ('/coroutine/11')
        assert resp.status_code == 200
        assert "pypi" in resp.text
        assert resp.data ['b'] == 'mask'
        assert resp.data ['c'] == 100
