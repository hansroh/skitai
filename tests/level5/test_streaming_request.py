import sys
import rs4
import pytest
import time

def stream (blocksize = 4096):
    chunks = 100
    while chunks:
        data = b'a' * blocksize
        if not data:
            break
        print ('send', blocksize)
        yield data
        chunks -= 1

def test_stream ():
    for x in stream ():
        assert len (x) == 4096

def test_streaming_request (launch, is_pypy):
    serve = './examples/app2.py'
    with launch (serve, port = 30371) as engine:
        for i in range (2):
            resp = engine.http.post (
                '/coroutine_streaming',
                data = stream (),
                headers = {'Content-Type': 'application/octet-stream'}
            )
            assert len (resp.text) == 409626


def test_streaming_request2 (launch, is_pypy):
    serve = './examples/app2.py'
    with launch (serve, port = 30371) as engine:
        for i in range (1):
            resp = engine.http.post (
                '/coroutine_streaming2',
                data = stream (65536),
                headers = {'Content-Type': 'application/octet-stream'}
            )
            assert len (resp.text) == 6554005
