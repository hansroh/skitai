from atila import Atila
import confutil
import skitai
from rs4 import asyncore
import os
import time

def test_route_empty (app):
    @app.route ("/")
    def index (context):
        assert 1 == 0

    @app.route ("/2")
    def index2 (context):
        assert 1 == 0, 'mismatch'

    @app.route ("/3")
    def index3 (context):
        assert 1 == 0, context.Error ('488 Error', 'asdada')

    @app.route ("/4")
    def index3 (context):
        assert False, context.Error ('488 Not My Fault', 'asdada')

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 502

        resp = cli.get ("/2")
        assert resp.status_code == 502

        resp = cli.get ("/3")
        assert resp.status_code == 488

        resp = cli.get ("/4")
        assert resp.status_code == 488
        assert resp.reason == 'Not My Fault'
