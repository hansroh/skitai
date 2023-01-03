import sys

def visit (engine, http3 = False):
    cli = engine.http3 if http3 else engine.http2

    resp = cli.get ('/nchar?n=167363')
    assert len (resp.text) == 167363

    if sys.version_info >= (3, 6) and not http3:
        assert '=":30371"; ma=86400' in resp.headers ['alt-svc']

    resp = cli.get ('/hello?num=1')
    assert resp.text == 'hello'

    resp = cli.get ('/hello?num=2')
    assert resp.text == 'hello\nhello'

    resp = cli.post ('/hello', {'num': 2})
    assert resp.text == 'hello\nhello'

    resp = cli.get ('/nchar?n=4736300')
    assert len (resp.text) == 4736300

    resp = cli.post ('/post', {'username': 'a' * 1000000})
    assert len (resp.text) == 1000006


def test_http23 (launch, is_pypy):
    if sys.version_info < (3, 7):
        return
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        visit (engine, False)
        if is_pypy:
            return
        if sys.version_info [:2] >= (3, 7):
            visit (engine, True)
