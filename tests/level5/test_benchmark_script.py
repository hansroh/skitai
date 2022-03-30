import pytest
import os, sys
is_pypy = '__pypy__' in sys.builtin_module_names

def test_launch (launch):
    if is_pypy:
        return
    serve = '../benchmark/run-skitai-atila.py'
    with launch (serve) as engine:
        resp = engine.axios.get ('/bench')
        assert resp.status_code == 200
        assert 'txs' in resp.data
        assert 'record_count' in resp.data

        resp = engine.axios.get ('/bench/sp')
        assert resp.status_code == 200
        assert 'txs' in resp.data
        assert 'record_count' in resp.data

        resp = engine.axios.get ('/bench/mix')
        assert resp.status_code == 200
        assert 'txs' in resp.data
        assert 'record_count' in resp.data

        resp = engine.axios.get ('/bench/one')
        assert resp.status_code == 200
        assert 'txs' in resp.data

        if os.environ.get ("CI_COMMIT_TITLE"):
            return

        resp = engine.axios.get ('/bench/http')
        assert resp.status_code == 200

        resp = engine.axios.get ('/bench/http/requests')
        assert resp.status_code == 200
