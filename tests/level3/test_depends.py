import skitai
import confutil
import pprint
import re
import time

def test_error_handler (app):
    def inspect (context):
        if int (context.request.args ["limit"]) != 100:
            raise context.HttpError ("400 Bad Request")

    def alter1 (context, response):
        response ["b"] = 200
        return response

    def alter2 (context, response):
        response ["c"] = 300
        return response

    @app.route ("/")
    @app.spec (limit = int)
    @app.depends (inspect, [alter1, alter2])
    def index (context, limit):
        return context.API (a = 100)

    async def inspecta (context):
        if int (context.request.args ["limit"]) != 100:
            raise context.HttpError ("400 Bad Request")

    async def alter1a (context):
        app.g.K = 600

    @app.route ("/async")
    @app.spec (limit = int)
    @app.depends (inspecta, alter1a)
    async def index2 (context, limit):
        return context.API (a = 100)

    @app.route ("/K")
    def index3 (context):
        return context.API (K = app.g.K)

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