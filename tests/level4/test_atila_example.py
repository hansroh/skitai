import pytest
import os, sys
is_pypy = '__pypy__' in sys.builtin_module_names

def test_launch (launch):
    serve = '../../atila/example/serve.py'
    if not os.path.isfile (serve):
        return

    with launch (serve) as engine:
        ws = engine.websocket ("/websocket/echo")
        ws.send ("Hello, World")
        result =  ws.recv()
        assert result =="echo: Hello, World"

        resp = engine.get ("/")
        assert resp.text.find ("Example") > 0

        resp = engine.get ("/apis/xxx")
        assert resp.status_code == 404

        resp = engine.get ("/apis/urlfor")
        assert resp.data == {'urls': ['/apis?message=urlfor', '/apis', '/apis/db', '/templates', '/templates?message=urlfor', '/templates/api-examples']}

        resp = engine.get ("/templates")
        assert resp.text.find ("Example") > 0

        resp = engine.get ("/templates/api-examples")
        assert resp.text.find ("Example") > 0

        resp = engine.axios.get ('/apis')
        assert resp.status_code == 200
        assert 'your_message' in resp.data

        resp = engine.axios.get ('/apis/xmlrpc')
        assert resp.status_code == 200
        assert 'method_name' in resp.data

        resp = engine.axios.get ('/apis/process')
        assert resp.status_code == 200
        assert 'result' in resp.data
        assert resp.data ['result'] == [1,2,3]
        assert resp.data ['duration'] < 3.0

        resp = engine.axios.get ('/apis/subprocess')
        assert resp.status_code == 200
        assert 'result' in resp.data
        assert 'serve.py' in resp.data ['result']

        resp = engine.axios.get ("/apis/mixing")
        assert resp.status_code == 200
        assert 'a' in resp.data
        assert 'b' in resp.data
        assert 'c' in resp.data

        assert 'rs4' in resp.data ['b']
        assert resp.data ['c'] == None
        assert isinstance (resp.data ['a'], list)
        assert '.py' in resp.data ['f']

        for i in range (4):
            resp2 = engine.axios.get ('/apis/thread{}'.format (i % 2 == 1 and 2 or ''))
            assert resp2.status_code == 200
            assert 'result' in resp2.data
            assert resp2.data ['result'] == [1,2,3]
            if i == 0:
                assert resp2.data ['duration'] < 3.0

        for i in range (4):
            resp1 = engine.axios.get ('/apis/rest-api{}'.format (i % 2 == 1 and 2 or ''))
            assert resp1.status_code == 200
            assert 'result' in resp1.data
            assert 'info' in resp1.data ['result']

        if not is_pypy:
            for i in range (4):
                resp = engine.axios.get ('/apis/db{}'.format (i % 2 == 1 and 2 or ''))
                assert resp.status_code == 200
                assert 'rows' in resp.data
                assert len (resp.data ['rows']) > 1
