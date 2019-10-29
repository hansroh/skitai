import pytest
import os

def test_launch (launch):
    serve = '../../atila/example/serve.py'
    if not os.path.isfile (serve):
        return

    with launch (serve) as engine:
        for i in range (2):
            resp = engine.axios.get ('/apis/rest-api{}'.format (i == 1 and 2 or ''))
            assert resp.status_code == 200
            assert 'result' in resp.data
            assert 'info' in resp.data ['result']

        for i in range (2):
            resp = engine.axios.get ('/apis/rest-api{}'.format (i == 1 and 2 or ''))
            assert resp.status_code == 200
            assert 'result' in resp.data
            assert 'info' in resp.data ['result']
