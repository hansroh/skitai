import pytest
import os
import socket
import time
import sys
import threading
from aquests.protocols.http2.hyper.common.exceptions import ConnectionResetError
import platform
IS_PYPY = platform.python_implementation() == 'PyPy'

def test_http3_close (launch):
    if sys.version_info < (3, 6):
        return

    from aioquic.quic.events import ConnectionTerminated
    from aquests.protocols.http3.events import ConnectionShutdownInitiated

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        for i in range (7): # need a little lucky
            mc = engine.http3.MultiCall ()
            for i in range (10):
                mc.get ('/hello?num=1')
            mc.get ('/shutdown?stream_id=4')
            mc.get ('/delay?wait=3')

            resps = mc.request ()
            assert len (resps) == 12

            wanted = [0, 0]
            for event in mc.control_event_history:
                if isinstance (event, ConnectionTerminated):
                    wanted [0] = 1
                elif isinstance (event, ConnectionShutdownInitiated):
                    wanted [1] = 1
            if wanted == [1, 1]:
                break
        assert wanted == [1, 1]

def test_http3_dup_push (launch):
    if sys.version_info < (3, 6):
        return

    from aioquic.quic.events import ConnectionTerminated
    from aquests.protocols.http3.events import ConnectionShutdownInitiated, DuplicatePushReceived

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        for j in range (7): # need a little lucky
            mc = engine.http3.MultiCall ()
            for i in range (3):
                mc.get ('/promise')
                mc.get ('/promise')
                mc.get ('/hello')
                mc.get ('/delay?wait=2')
                mc.get ('/test')
                mc.get ('/delay?wait=2')
                mc.get ('/hello')
                mc.get ('/promise')
                mc.get ('/promise')
                mc.get ('/delay?wait=2')
                mc.get ('/test')
                mc.get ('/hello')
                mc.get ('/delay?wait=2')
                mc.get ('/test')
                mc.get ('/promise')
                mc.get ('/hello')
                mc.get ('/test')

            resps = mc.request ()
            dup = 0
            for event in mc.control_event_history:
                if isinstance (event, DuplicatePushReceived):
                    dup += 1
            if dup:
                break

        assert dup
