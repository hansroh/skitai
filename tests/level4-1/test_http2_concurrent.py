
from rs4.protocols.sock.impl.http2.hyper.http20.h2.exceptions import ProtocolError
from rs4.protocols.sock.impl.http2.hyper.common.exceptions import ConnectionResetError

def test_http2 (launch):
    serve = './examples/https.py'
    with launch (serve, port = 30371,ssl = True) as engine:
        resp = engine.http2.get ('/hello')
        assert resp.status_code == 200

def test_http2_push (launch):
    serve = './examples/https.py'
    with launch (serve, port = 30371, ssl = True) as engine:
        pushes = 0
        for i in range (10): # need a little lucky
            mc = []
            for i in range (3):
                mc.append ('/promise')
                mc.append ('/promise')
                mc.append ('/hello')
                mc.append ('/delay?wait=2')
                mc.append ('/test')
                mc.append ('/delay?wait=2')
                mc.append ('/hello')
                mc.append ('/promise')
                mc.append ('/promise')
                mc.append ('/delay?wait=2')
                mc.append ('/test')
                mc.append ('/hello')
                mc.append ('/delay?wait=2')
                mc.append ('/test')
                mc.append ('/promise')
                mc.append ('/hello')
                mc.append ('/test')

            resps = engine.http2.get (mc)
            for resp in resps:
                for prom in resp.get_pushes ():
                    pushes += 1

        assert pushes >= 70
