import pytest
import time

def test_launch (launch):
    with launch ("./examples/app.py") as engine:
        resp = engine.get ("/")
        assert resp.text.find ("Copyright (c) 2015-present, Hans Roh") > 0

        resp = engine.api ().json.get ()
        assert resp.data ["data"] == "JSON"

        time.sleep (1.0)


def test_launch2 (launch):
    engine = launch ("./examples/app.py")
    resp = engine.get ("/")
    assert resp.text.find ("Copyright (c) 2015-present, Hans Roh") > 0

    resp = engine.api ().json.get ()
    assert resp.data ["data"] == "JSON"

    time.sleep (1.0)


