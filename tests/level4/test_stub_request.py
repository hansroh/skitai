def test_app (launch):
    with launch ("./examples/app2.py") as engine:
        resp = engine.get ('/stub')
        assert resp.status_code == 200
        r = resp.data ['result']
        assert len (r) == 4
        for each in r:
            assert each.find ('rs4') > -1
