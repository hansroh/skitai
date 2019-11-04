import pytest
import os
import socket
import time
from aquests.protocols.http3 import requests

def test_http2 (launch):
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http2.get ('/hello?num=1')
        assert resp.text == 'hello'
        resp = engine.http2.get ('/hello?num=2')
        assert resp.text == 'hello\nhello'

        resp = engine.http2.post ('/hello', {'num': 2})
        assert resp.text == 'hello\nhello'

def test_http3 (launch):
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

