import pytest
import sys, os
from aquests.protocols.http2.hyper import HTTPConnection

#@pytest.mark.skip
def test_h2c (launch):
    with launch ("./examples/app.py") as engine:
        conn = HTTPConnection('127.0.0.1:30371', enable_push=False, secure=False)

        conn.request('GET', '/hello')
        response = conn.get_response()
        assert response.read() == b'hello'
        assert response.status == 200

        conn.request('GET', '/100.htm')
        response = conn.get_response()
        assert response.status == 200

        conn.request('GET', '/0.htm')
        response = conn.get_response()
        assert response.status == 200

def test_h2 (launch):
    with launch ("./examples/https.py") as engine:
        conn = HTTPConnection('127.0.0.1:30371', secure=True)

        conn.request('GET', '/hello')
        response = conn.get_response()
        assert response.read() == b'hello'
        assert response.status == 200

        conn.request('GET', '/100.htm')
        response = conn.get_response()
        assert response.status == 200

        conn.request('GET', '/0.htm')
        response = conn.get_response()
        assert response.status == 200

        conn.request('GET', '/reindeer.jpg')
        response = conn.get_response()
        etag = response.headers [b'etag'][0].decode ()
        assert response.status == 200

        conn.request('GET', '/reindeer.jpg', headers = {"If-None-Match": etag})
        response = conn.get_response()
        assert response.status == 304

        for i in range (10):
            conn = HTTPConnection('127.0.0.1:30371', secure=True)
            conn.request('GET', '/reindeer.jpg', headers = {"If-None-Match": etag})
            response = conn.get_response()
            assert response.status == 304

