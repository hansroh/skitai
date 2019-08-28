from atila import Atila
import confutil
import skitai
from rs4 import asyncore
import os
from rs4 import jwt as jwt_
import time

def test_route_empty (app):
    app._mount_option ["point"] = "/beta"

    @app.route ("/")
    def index2 (was, path = None):
        return "Hello, World"

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/beta")
        assert resp.status_code == 301

        resp = cli.get ("/beta/")        
        assert resp.status_code == 200

        resp = cli.get ("/beta/1")        
        assert resp.status_code == 404


    @app.route ("")
    def index (was, path = None):
        return "Hello, World"

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/beta")
        assert resp.text == "Hello, World"

        resp = cli.get ("/beta/")        
        assert resp.status_code == 200

        resp = cli.get ("/beta/1")        
        assert resp.status_code == 404
