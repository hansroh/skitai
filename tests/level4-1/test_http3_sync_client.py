import pytest
import os
import socket
import time
import sys

def test_http3 (launch):
    if sys.version_info < (3, 6):
        return

    from aquests.protocols.http3 import client

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        s = client.Connection ('127.0.0.1:30371')
        resp = s.get ('/hello?num=1')
        assert resp.data == b'hello'

        resp = s.get ('/promise')
        assert len (resp.promises) == 2
        assert resp.headers [b':status'] == b'200'


def test_http3_2 (launch):
    if sys.version_info < (3, 6):
        return

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http3.get ('/hello?num=1')
        assert resp.text == 'hello'
        assert resp.status_code == 200
