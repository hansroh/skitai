import sys
is_pypy = '__pypy__' in sys.builtin_module_names

def test_http2 (launch):
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.http2.get ('/lb/project/rs4/')
        assert 'pip install rs4' in resp.text

        resp = engine.http2.get ('/nchar?n=167363')
        assert len (resp.text) == 167363

        if not is_pypy:
            resp = engine.http2.get ('/nchar?n=4736300')
            assert len (resp.text) == 4736300

        resp = engine.http2.get ('/hello?num=1')
        assert resp.text == 'hello'

        if sys.version_info >= (3, 6):
            assert '=":30371"; ma=86400' in resp.headers ['alt-svc']

        resp = engine.http2.get ('/hello?num=2')
        assert resp.text == 'hello\nhello'

        resp = engine.http2.post ('/hello', {'num': 2})
        assert resp.text == 'hello\nhello'

        resp = engine.http2.post ('/post', {'username': 'a' * 1000000})
        assert len (resp.text) == 1000006
