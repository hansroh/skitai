from atila import Atila
import confutil
import skitai
from rs4 import asyncore
import os
import time

def test_route_root (app, dbpath):
    @app.route ("/<path:path>")
    @app.route ("/")
    def index (was, path = None):
        return "Hello, World"

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.text == "Hello, World"

        resp = cli.get ("/hello")
        assert resp.text == "Hello, World"
