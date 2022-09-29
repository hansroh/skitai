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
    @app.route ("/hello")
    @app.route ("/")
    def index (context):
        return "Hello, World"

    @app.route ("/petse/<int:id>")
    def pets_error (context):
        return "Pets"

    @app.route ("/pets/<int:id>", methods = ["GET", "POST"])
    def pets (context, id = None):
        return "Pets{}".format (id)

    @app.route ("/pets2/<int:id>", methods = ["POST"])
    def pets2 (context, id = None, a = 0):
        return "Pets{}".format (id)

    @app.route ("/pets3/<int:id>")
    def pets3 (context, id = None):
        return "Pets{}".format (id)

    @app.route ("/echo")
    def echo (context, m):
        return m

    @app.route ("/json")
    def json (context, m):
        return context.response.api (data = m)

    @app.route ('/jwt')
    @app.authorization_required ("bearer")
    def jwt (context):
        return context.response.api (context.request.JWT)

    @app.maintain
    def increase (context, now, count):
        if "total-user" in app.store:
            app.store.set ("total-user", app.store.get ("total-user") + 100)

    @app.route ("/getval")
    def getval (context):
        ret = str (app.store.get ("total-user"))
        return ret

    @app.maintain (2)
    def increase2 (context, now, count):
        if "total-user2" in app.store:
            app.store.set ("total-user2", app.store.get ("total-user2") + 100)

    @app.route ("/getval2")
    def getval2 (context):
        ret = str (app.store.get ("total-user2"))
        return ret

    @app.route ("/rpc2/add_number")
    def add_number (context, a, b):
        return a + b

    @app.route ("/routeguide.RouteGuide/GetFeature")
    def GetFeature (context, point):
        feature = get_feature(db, point)
        if feature is None:
            return route_guide_pb2.Feature(name="", location=point)
        else:
            return feature

    with app.test_client ("/", confutil.getroot ()) as cli:
        with cli.jsonrpc ('/rpc2') as stub:
            assert stub.add_number (1, 3) == 4
            assert stub.add_number (2, 3) == 5

        with cli.rpc ('/rpc2') as stub:
            assert stub.add_number (1, 3) == 4

        with pytest.raises (NotImplementedError):
            with cli.grpc ('/routeguide.RouteGuide') as stub:
                point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
                print (stub.GetFeature (point))

        resp = cli.get ("/")
        assert resp.text == "Hello, World"

        resp = cli.get ("/hello")
        assert resp.text == "Hello, World"

        resp = cli.get ("/petse/1")
        assert resp.status_code == 530

        resp = cli.get ("/pets/1")
        assert resp.status_code == 200
        assert resp.text == "Pets1"

        resp = cli.post ("/pets", {"a": 1})
        assert resp.status_code == 400

        resp = cli.get ("/pets")
        assert resp.status_code == 200

        resp = cli.get ("/pets2/1")
        assert resp.status_code == 405

        resp = cli.post ("/pets2/1", {"id": 1})
        assert resp.status_code == 200

        resp = cli.post ("/pets2", {"a": 1})
        assert resp.status_code == 200
        assert resp.text == "PetsNone"

        resp = cli.get ("/pets2")
        assert resp.status_code == 405

        resp = cli.get ("/pets3")
        assert resp.text == "PetsNone"

        resp = cli.get ("/pets3/1")
        print (resp)
        assert resp.text == "Pets1"

        resp = cli.get ("/echo?m=GET")
        assert resp.text == "GET"

        resp = cli.post ("/json", {"m": "POST"})
        assert '"data":' in resp.text
        assert '"POST"' in resp.text

        resp = cli.post ("/json", {"m": "POST"})
        assert '"data":' in resp.text
        assert '"POST"' in resp.text

        app.securekey = "securekey"
        resp = cli.get ("/jwt", headers = {"Authorization": "Bearer {}".format (jwt_.gen_token (app.salt, {"exp": 3000000000, "username": "hansroh"}))})
        assert resp.data == {'exp': 3000000000, 'username': 'hansroh'}

        resp = cli.get ("/jwt", headers = {"Authorization": "Bearer {}".format (jwt_.gen_token (app.salt, {"exp": 1, "username": "hansroh"}))})
        assert resp.code == 401
        app.securekey = None

        if is_pypy:
            return

        app.config.MAINTAIN_INTERVAL = 1
        app.g.set ("total-user", 100)
        for i in range (4):
            time.sleep (1)
            resp = cli.get ("/getval")
        assert int (resp.text) >= 200

        app.g.set ("total-user2", 100)
        resp = cli.get ("/getval2")
        assert int (resp.text) <= 200

        for i in range (8):
            time.sleep (1)
            resp = cli.get ("/getval2")

        resp = cli.get ("/getval2")
        assert int (resp.text) >= 400

        resp = cli.get ("/getval")
        assert int (resp.text) >= 400

