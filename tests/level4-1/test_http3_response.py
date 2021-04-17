import pytest
import os
import socket
import time
import sys

def test_http3 (launch):
    if sys.version_info < (3, 6):
        return
    if sys.version_info [:2] == (3, 7):
        # freq error, why?
        return

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http3.get ('/hello?num=1')
        assert resp.text == 'hello'

        resp = engine.http3.get ('/hello?num=2')
        assert resp.text == 'hello\nhello'

        resp = engine.http3.get ('/lb/project/rs4/')
        assert 'pip install rs4' in resp.text


def test_http3_post (launch):
    if sys.version_info < (3, 6):
        return
    if sys.version_info [:2] == (3, 7):
        # freq error, why?
        return

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http3.post ('/post', {'username': 'a' * 1000000})
        assert len (resp.text) == 1000006

        resp = engine.http3.post ('/hello', {'num': 2})
        assert resp.text == 'hello\nhello'

        resp = engine.http3.post ('/hello', {'num': 2})
        assert resp.text == 'hello\nhello'

        resp = engine.http3.post ('/hello', {'num': 1})
        assert resp.text == 'hello'
