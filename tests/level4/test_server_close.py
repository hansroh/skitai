import pytest
import os
import socket
import time
import sys
import threading
from aquests.protocols.http2.hyper.common.exceptions import ConnectionResetError

def test_http2 (launch):
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http2.get ('/hello?num=1')
        assert resp.text == 'hello'

        resp = engine.http2.get ('/shutdown?stream_id=3')
        assert resp.text == 'CLOSED'
        with pytest.raises (ConnectionResetError):
            resp = engine.http2.get ('/delay?wait=3')

def test_http3 (launch):
    if sys.version_info < (3, 6):
        return

    from aioquic.quic.events import ConnectionTerminated
    try:
        from aioquic.h3.events import ConnectionShutdownInitiated
    except ImportError:
        ConnectionShutdownInitiated = int # dummy type

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        mc = engine.http3.MultiCall ()
        for i in range (10):
            mc.get ('/hello?num=1')
        mc.get ('/shutdown?stream_id=4')
        mc.get ('/delay?wait=3')

        resps = mc.request ()
        assert len (resps) == 12

        wanted = [0, ConnectionShutdownInitiated is int and 1 or 0]
        for event in mc.control_event_history:
            if isinstance (event, ConnectionTerminated):
                wanted [0] = 1
            elif isinstance (event, ConnectionShutdownInitiated):
                wanted [1] = 1
        assert wanted == [1, 1]


