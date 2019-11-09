import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time
import aquests

def test_http3_server_push (launch):
    if sys.version_info < (3, 6):
        return
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http3.get ('/promise')
        pathes = []
        for push in resp.get_pushes(): # all pushes promised before response headers
            pathes.append (push.path)
        assert b'/hello' in pathes
        assert b'/test' in pathes
        data = resp.content
        assert b'"data": "JSON"' in data

        resp = engine.http3.get ('/promise', allow_push = False)
        pathes = []
        for push in resp.get_pushes(): # all pushes promised before response headers
            pathes.append (push.path)
        assert b'/hello' not in pathes
        assert b'/test' not in pathes
        data = resp.content
        assert b'"data": "JSON"' in data

        resp = engine.http3.get ('/hello')
        resp = engine.http3.get ('/test')
