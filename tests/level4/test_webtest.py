
def test_app_run (launch):
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        resp = engine.get ('/')
        assert resp.status_code == 200

        resp = engine.http.get ('/')
        assert resp.status_code == 200

        resp = engine.http2.get ('/')
        assert resp.status_code == 200

        resp = engine.http3.get ('/')
        assert resp.status_code == 200

        resp = engine.axios.get ('/delay?wait=0.1')
        assert resp.status_code == 200
        assert resp.json () ['data'] == "JSON"

        resp = engine.siesta.delay.get (wait = 0.1)
        assert resp.status_code == 200
        assert resp.json () ['data'] == "JSON"

        with engine.stub ('/') as stub:
            resp = stub.get ('/delay?wait=0.1')
            assert resp.status_code == 200
            assert resp.json () ['data'] == "JSON"

        resp = engine.http2.get ('/promise')
        assert resp.status_code == 200
        assert len (resp.get_pushes ()) == 2

        resp = engine.http3.get ('/promise')
        assert resp.status_code == 200
        assert len (resp.get_pushes ()) == 2
