import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time

def test_http3_server_push (launch):
    if sys.version_info < (3, 7):
        return
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http3.get ('/promise')
        pathes = []
        for push in resp.get_pushes(): # all pushes promised before response headers
            pathes.append (push.path)
        assert '/hello' in pathes
        assert '/test' in pathes
        data = resp.content
        assert b'"data":' in data
        assert b'"JSON"' in data

        resp = engine.http3.get ('/hello')
        resp = engine.http3.get ('/test')
