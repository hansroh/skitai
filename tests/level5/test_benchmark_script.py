import pytest
import os, sys
is_pypy = '__pypy__' in sys.builtin_module_names

def test_atila (launch):
    if is_pypy:
        return
    serve = '../benchmark/run-skitai-atila.py'
    with launch (serve) as engine:
        resp = engine.axios.get ('/bench')
        assert resp.status_code == 200
        assert 'txs' in resp.data
        assert 'record_count' in resp.data

        resp = engine.axios.get ('/bench/async')
        assert resp.status_code == 200
        assert 'txs' in resp.data
        assert 'record_count' in resp.data

        resp = engine.axios.get ('/bench/sqlphile')
        assert resp.status_code == 200
        assert 'txs' in resp.data
        assert 'record_count' in resp.data

        resp = engine.axios.get ('/bench/delay?t=1.0')
        assert resp.status_code == 200
        assert 'txs' in resp.data
        assert 'record_count' in resp.data

        resp = engine.axios.get ('/bench/http')
        assert resp.status_code == 200

        resp = engine.axios.get ('/bench/http/dual')
        assert resp.status_code == 200

        resp = engine.axios.get ('/bench/http/requests')
        assert resp.status_code == 200


def test_django (launch):
    if is_pypy:
        return
    serve = '../benchmark/run-skitai-django.py'
    with launch (serve) as engine:
        resp = engine.axios.get ('/bench')
        assert resp.status_code == 200
        assert 'txs' in resp.data
        assert 'record_count' in resp.data
