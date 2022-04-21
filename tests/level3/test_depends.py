import skitai
import confutil
import pprint
import re
import time

def test_error_handler (app):
    def inspect (was):
        if int (was.request.args ["limit"]) != 100:
            raise was.Error ("400 Bad Request")

    def alter1 (was, response):
        response ["b"] = 200
        return response

    def alter2 (was, response):
        response ["c"] = 300
        return response

    @app.route ("/")
    @app.spec (limit = int)
    @app.depends (inspect, [alter1, alter2])
    def index (was, limit):
        return was.API (a = 100)

    async def inspecta (was):
        if int (was.request.args ["limit"]) != 100:
            raise was.Error ("400 Bad Request")

    async def alter1a (was):
        app.g.K = 600

    @app.route ("/async")
    @app.spec (limit = int)
    @app.depends (inspecta, alter1a)
    async def index2 (was, limit):
        return was.API (a = 100)

    @app.route ("/K")
    def index3 (was):
        return was.API (K = app.g.K)

    with app.test_client ("/", confutil.getroot (), enable_async = True) as cli:
        resp = cli.get ("/?limit=100")
        assert resp.status_code == 200
        assert resp.data ["a"] == 100
        assert resp.data ["b"] == 200
        assert resp.data ["c"] == 300

        resp = cli.get ("/?limit=200")
        assert resp.status_code == 400

        resp = cli.get ("/async?limit=100")
        assert resp.status_code == 200
        assert resp.data ["a"] == 100
        assert "b" not in resp.data

        time.sleep (1)

        resp = cli.get ("/K")
        assert resp.status_code == 200
        assert resp.data ["K"] == 600