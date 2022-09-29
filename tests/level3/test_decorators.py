from atila import Atila
import confutil
import skitai
from rs4 import asyncore
import os
from rs4.webkit import jwt as jwt_
import time
import route_guide_pb2
import pytest

def test_cli (app, dbpath, is_pypy):
    def test (context):
        context.request.g.target = 'World'

    @app.route ("/")
    @app.testpass_required (test)
    def index (context):
        return "Hello, {}".format (context.request.g.target)

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.text == "Hello, World"
