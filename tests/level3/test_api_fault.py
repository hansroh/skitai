from atila import Atila
import confutil
import skitai
from rs4 import asyncore
import os
import time

def test_route_root (app, dbpath):
    @app.route ("/index")
    @app.require ("URL", ints = ["t"])
    def index (was, t = 0):
        t = int (t)
        if t == 0:
            return was.API ("200 OK")
        if t == 1:
            return was.API ("205 No Content")
        if t == 2:
            return was.API ("201 Created", {"data": 1})
        if t == 3:
            return was.API ("201 Created", data = 1)
        if t == 4:
            return was.API (data = 1)
        if t == 5:
            return was.API ({"data": 1})
        if t == 9:
            return was.API ("201 Created", {"data": 1}, data = 2)

    with app.test_client ("/", confutil.getroot ()) as cli:
        api = cli.api ()
        resp = api.index.get (t = 0)
        assert resp.status_code == 200

        resp = api.index.get (t = 1)
        assert resp.status_code == 205
        assert resp.data == {}

        resp = api.index.get (t = 2)
        assert resp.status_code == 201
        assert resp.data == {"data": 1}

        resp = api.index.get (t = 3)
        assert resp.status_code == 201
        assert resp.data == {"data": 1}

        resp = api.index.get (t = 4)
        assert resp.status_code == 200
        assert resp.data == {"data": 1}

        resp = api.index.get (t = 5)
        assert resp.status_code == 200
        assert resp.data == {"data": 1}

        resp = api.index.get (t = 9)
        assert resp.status_code == 201
        assert resp.data == {"data": 2}
