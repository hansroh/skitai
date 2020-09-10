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
