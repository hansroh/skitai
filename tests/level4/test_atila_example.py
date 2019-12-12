import pytest
import os
from websocket import create_connection

def test_launch (launch):
    serve = '../../atila/example/serve.py'
    if not os.path.isfile (serve):
        return

    with launch (serve) as engine:

        ws = create_connection("ws://127.0.0.1:30371/websocket/echo")
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

        for i in range (4):
            resp = engine.axios.get ('/apis/db{}'.format (i % 2 == 1 and 2 or ''))
            assert resp.status_code == 200
            assert 'rows' in resp.data
            assert len (resp.data ['rows']) > 1
