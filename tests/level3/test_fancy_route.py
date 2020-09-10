from atila import Atila
import confutil
import skitai
from rs4 import asyncore
import os
import time

def test_route (app):
    @app.route ("/owners/<oid>")
    def index (was, oid= 1, p1 = 3):
        return "Hello, World"

    @app.route ("/owners/<oid>/pets/<int:pid>")
    def index2 (was, oid, pid = 1, p1 = 3):
        return "Hello, World"

    @app.route ("/link1")
    def link1 (was, oid = None):
        if oid:
            return was.urlfor (index, 4)
        else:
            return was.urlfor (index)

    @app.route ("/link2")
    def link2 (was, pid = None):
        if pid:
            return was.urlfor (index2, 7, pid)
        else:
            return was.urlfor (index2, 7)

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/owners")
        assert resp.status_code == 200
        assert resp.text == "Hello, World"

        resp = cli.get ("/owners/54")
        assert resp.status_code == 200
        assert resp.text == "Hello, World"

        resp = cli.get ("/owners/54/pets/5")
        assert resp.status_code == 200
        assert resp.text == "Hello, World"

        resp = cli.get ("/owners/54/pets")
        assert resp.status_code == 200
        assert resp.text == "Hello, World"

        resp = cli.get ("/link1")
        assert resp.status_code == 200
        assert resp.text == "/owners"

        resp = cli.get ("/link1?oid=4")
        assert resp.status_code == 200
        assert resp.text == "/owners/4"

        resp = cli.get ("/link2?pid=123")
        assert resp.status_code == 200
        assert resp.text == "/owners/7/pets/123"

        resp = cli.get ("/link2")
        assert resp.status_code == 200
        assert resp.text == "/owners/7/pets"

