def test_webtest_unsecure (launch):
    try:
        import tfserver
    except ImportError:
        return

    serve = './level4/serve.py'
    with launch (serve, port = 30371) as engine:
        resp = engine.get ('/')
        assert resp.status_code == 200
        assert resp.text == 'pwa'

        resp = engine.get ('/sub2')
        assert resp.status_code == 200
        assert resp.text == 'sub2'

        resp = engine.get ('/sub2/sub3')
        assert resp.status_code == 200
        assert resp.text == 'sub3'

        resp = engine.get ('/sub2/sub4')
        assert resp.status_code == 200
        assert resp.text == 'sub4'

        resp = engine.get ('/sub10')
        assert resp.status_code == 200
        assert resp.text == 'sub10'

        resp = engine.get ('/sub10/sub3')
        assert resp.status_code == 200
        assert resp.text == 'sub3'

        resp = engine.get ('/sub10/sub4')
        assert resp.status_code == 200
        assert resp.text == 'sub4'

        resp = engine.get ('/sub10/sub4/sub5')
        assert resp.status_code == 200
        assert resp.text == 'sub5'

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
