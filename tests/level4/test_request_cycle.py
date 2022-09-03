def test_request_cycle (launch):
    serve = './level4/serve.py'
    with launch (serve, port = 30371) as engine:
        resp = engine.get ('/')
        assert resp.status_code == 200
        assert resp.text == 'pwa'

        resp = engine.get ('/sub2')
        assert resp.status_code == 200
        assert resp.text == 'sub2-trailer'

        resp = engine.get ('/sub2/sub4')
        assert resp.status_code == 200
        assert resp.text == 'sub4-async-trailer'

        resp = engine.get ('/sub2/async')
        assert resp.status_code == 200
        assert resp.text == 'sub2-trailer'

        resp = engine.get ('/sub2/sub4/async')
        assert resp.status_code == 200
        assert resp.text == 'sub4-async-trailer'