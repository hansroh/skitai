def test_webtest_unsecure (launch):
    serve = './level4/serve.py'
    with launch (serve, port = 30371) as engine:
        resp = engine.get ('/')
        assert resp.status_code == 200
        assert resp.text == 'pwa'

        resp = engine.get ('/examples')
        assert resp.status_code == 200
        assert 'FranckFreiburger' in resp.text

        resp = engine.get ('/admin')
        assert resp.status_code == 200
        assert '/admin/static' in resp.text

        resp = engine.get ('/reindeer.jpg')
        assert resp.status_code == 200

        resp = engine.axios.get ('/models')
        assert 'models' in resp.data
        assert resp.status_code == 200

        resp = engine.get ('/models/tfserver')
        assert resp.text == 'tfserver'
        assert resp.status_code == 200

        resp = engine.get ('/delune')
        assert resp.text == '<h1>Delune</h1>'
        assert resp.status_code == 200

        resp = engine.get ('/delune/delune-ext')
        assert resp.text == 'delune-ext'
        assert resp.status_code == 200

        resp = engine.get ('/static/delune/reindeer.jpg')
        assert resp.status_code == 200
