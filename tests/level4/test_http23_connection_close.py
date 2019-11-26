import pytest
import os
import socket
import time
import sys
import threading
from aquests.protocols.http2.hyper.common.exceptions import ConnectionResetError
import platform
IS_PYPY = platform.python_implementation() == 'PyPy'

def test_http2 (launch):
    if IS_PYPY:
        # aquests.protocols.http2.hyper hans secure connection problem
        return
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http2.get ('/hello?num=1')
        assert resp.text == 'hello'

        resp = engine.http2.get ('/shutdown?stream_id=3')
        assert resp.text == 'CLOSED'
        try:
            resp = engine.http2.get ('/delay?wait=3')
        except Exception as e:
            assert isinstance (e, (ConnectionResetError, socket.timeout))

def test_http3 (launch):
    if sys.version_info < (3, 6):
        return

    from aioquic.quic.events import ConnectionTerminated
    from aquests.protocols.http3.events import ConnectionShutdownInitiated
    from aquests.protocols.http3.client import ConnectionClosed

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        for i in range (3):
            resp = engine.http3.get ('/hello?num=1')
        resp = engine.http3.get ('/shutdown?stream_id=12')
        assert resp.text == 'CLOSED'

        try:
            resp = engine.http2.get ('/hello?num=1')
        except Exception as e:
            assert isinstance (e, (ConnectionClosed, socket.timeout))
