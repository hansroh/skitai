import sys
import rs4

def stream (blocksize = 4096):
    chunks = 100
    while chunks:
        data = b'a' * blocksize
        if not data:
            break
        yield data
        chunks -= 1

def test_stream ():
    for x in stream ():
        assert len (x) == 4096

def test_streaming_request (launch, is_pypy):
    serve = './examples/app2.py'
    with launch (serve, port = 30371) as engine:
        for i in range (1):
            resp = engine.http.post (
                '/coroutine_streaming',
                data = stream (),
                headers = {'Content-Type': 'application/octet-stream'}
            )
            assert len (resp.text) > (4096 * 90)
