import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time
import aquests
from aquests.protocols.http2.hyper import HTTPConnection

def test_http3_server_push (launch):
    if sys.version_info.major == 3 and sys.version_info.minor < 6:
        return
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http3.get ('/promise')
        print (resp.get_pushes ())

        pathes = []
        for push in resp.get_pushes(): # all pushes promised before response headers
            pathes.append (push.path)
        assert b'/hello' in pathes
        assert b'/test' in pathes

        data = resp.content
        assert b'"data": "JSON"' in data
        print(data)


