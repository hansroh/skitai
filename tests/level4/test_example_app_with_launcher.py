import pytest

def test_launch (launch):
    with launch ("./examples/app.py") as engine:
        resp = engine.get ("/")
        assert resp.text.find ("Copyright (c) 2015-present, Hans Roh") > 0

        resp = engine.api ().json.get ()
        assert resp.data ["data"] == "JSON"

        resp = engine.api ().was.get ()
        assert resp.data['a'] and not resp.data ['b']
        assert resp.data['c'] and not resp.data ['d']
        assert resp.data['e'] and not resp.data ['f']


