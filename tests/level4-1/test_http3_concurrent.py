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

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        mc = []
        for i in range (100):
            mc.append ('/hello?num=1')
        mc.append ('/delay?wait=3')
        resps = engine.http3.get (mc)
        assert len (resps) == 101

def test_http3_shutdown (launch):
    # 2021.4.17, after client is replaced with official aioquic
    # shutdown does not work properly
    if sys.version_info < (3, 6):
        return

    from aioquic.quic.events import ConnectionTerminated
    from aquests.protocols.http3.events import ConnectionShutdownInitiated

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        mc = []
        mc.append ('/shutdown?stream_id=0')
        resps = engine.http3.get (mc)
        assert resps [0].status_code == 200
        wanted = [0, 0]
        for resp in resps:
            for event in resp.events:
                print (event)
                if isinstance (event, ConnectionTerminated):
                    wanted [0] = 1
                elif isinstance (event, ConnectionShutdownInitiated):
                    wanted [1] = 1
        # assert wanted == [1, 1]

def test_http3_dup_push (launch):
    if sys.version_info < (3, 6):
        return

    from aioquic.quic.events import ConnectionTerminated
    from aquests.protocols.http3.events import ConnectionShutdownInitiated

    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        pushes = {}
        for j in range (3): # need a little lucky
            mc = []
            for i in range (3):
                mc.append ('/promise')
                mc.append ('/promise')
                mc.append ('/hello')
                mc.append ('/delay?wait=2')
                mc.append ('/test')
                mc.append ('/delay?wait=2')
                mc.append ('/hello')
                mc.append ('/promise')
                mc.append ('/promise')
                mc.append ('/delay?wait=2')
                mc.append ('/test')
                mc.append ('/hello')
                mc.append ('/delay?wait=2')
                mc.append ('/test')
                mc.append ('/promise')
                mc.append ('/hello')
                mc.append ('/test')

            resps = engine.http3.get (mc)
            for resp in resps:
                for prom in resp.get_pushes ():
                    if prom.push_id is not None:
                        try:
                            pushes [prom.push_id] += 1
                        except KeyError:
                            pushes [prom.push_id] = 1

        assert IS_PYPY and len (pushes) > 2 or len (pushes) == 8
        for k, v in pushes.items ():
            if IS_PYPY: # why?
                assert v
            else:
                assert v == 3
