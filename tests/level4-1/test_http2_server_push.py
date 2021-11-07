import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time
from skitai.protocols.sock.impl.http2.hyper import HTTPConnection

def test_http2_server_push (launch):
    with launch ("./examples/app.py") as engine:
        conn = HTTPConnection('127.0.0.1:30371', enable_push=True, secure=False)
        conn.request('GET', '/promise')
        response = conn.get_response()
        pathes = []
        for push in conn.get_pushes(): # all pushes promised before response headers
            pathes.append (push.path)
        assert b'/hello' in pathes
        assert b'/test' in pathes
        data = response.read()
        assert b'"data":' in data
        assert b'"JSON"' in data
        print(data)
