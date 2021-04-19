
def visit_pages (engine, http3 = False):
    resp = engine.get ('/')
    assert resp.status_code == 200

    resp = engine.http.get ('/')
    assert resp.status_code == 200

    resp = engine.http2.get ('/')
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

    if http3:
        resp = engine.http3.get ('/')
        assert resp.status_code == 200

        resp = engine.http3.get ('/promise')
        assert resp.status_code == 200
        assert len (resp.get_pushes ()) == 2


def test_webtest_unsecure (launch):
    serve = './examples/app.py'
    with launch (serve, port = 30371) as engine:
        visit_pages (engine)

def test_webtest_secure (launch):
    serve = './examples/https.py'
    with launch (serve, port = 30371, ssl = True) as engine:
        visit_pages (engine)

def test_webtest_h3 (launch):
    serve = './examples/http3.py'
    with launch (serve, port = 30371, quic = 30371, ssl = True) as engine:
        visit_pages (engine, True)
