from atila import Atila
import confutil
import skitai
from rs4 import asyncore
import os
from rs4 import jwt as jwt_
import time

def test_route_empty (app):
    @app.route ("/")
    def index (was):
        assert 1 == 0

    @app.route ("/2")
    def index2 (was):
        assert 1 == 0, 'mismatch'

    @app.route ("/3")
    def index3 (was):
        assert 1 == 0, was.Error ('488 Error', 'asdada')

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 502

        resp = cli.get ("/2")
        assert resp.status_code == 502

        resp = cli.get ("/3")
        assert resp.status_code == 488

