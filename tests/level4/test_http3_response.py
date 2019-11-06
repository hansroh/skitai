import pytest
import os
import socket
import time
import sys

#@pytest.mark.skip
def test_http2 (launch):
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http2.get ('/hello?num=1')
        assert resp.text == 'hello'
        if sys.version_info.major > 3 or (sys.version_info.major == 3 and sys.version_info.minor >= 6):
            assert resp.headers ['alt-svc'] == 'h3-23=":30371"; ma=86400'

        resp = engine.http2.get ('/hello?num=2')
        assert resp.text == 'hello\nhello'

        resp = engine.http2.post ('/hello', {'num': 2})
        assert resp.text == 'hello\nhello'

        resp = engine.http2.get ('/lb/project/rs4/')
        assert 'pip install rs4' in resp.text

        resp = engine.http2.post ('/post', {'username': 'a' * 1000000})
        assert len (resp.text) == 1000006

def test_http3 (launch):
    if sys.version_info.major == 3 and sys.version_info.minor < 6:
        return

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http3.get ('/hello?num=1')
        assert resp.text == 'hello'
        resp = engine.http3.get ('/hello?num=2')
        assert resp.text == 'hello\nhello'

        resp = engine.http3.post ('/hello', {'num': 2})
        assert resp.text == 'hello\nhello'

        resp = engine.http3.post ('/hello', {'num': 2})
        assert resp.text == 'hello\nhello'
        resp = engine.http3.post ('/hello', {'num': 1})
        assert resp.text == 'hello'

        resp = engine.http3.get ('/lb/project/rs4/')
        assert 'pip install rs4' in resp.text

        resp = engine.http3.post ('/post', {'username': 'a' * 1000000})
        assert len (resp.text) == 1000006

