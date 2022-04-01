import asyncio
import confutil
import json

def test_success (app):
    app.hooks_called = 0
    @app.before_request
    def before_request (was):
        app.hooks_called += 1

    @app.failed_request
    def failed_request (was, expt):
        app.hooks_called += 1

    @app.finish_request
    def finish_request (was):
        app.hooks_called += 1

    @app.teardown_request
    def teardown_request (was):
        app.hooks_called += 1

    @app.route ("/")
    async def a (was):
        await asyncio.sleep (1)
        return "100"

    @app.route ("/api")
    async def b (was, err = "no"):
        await asyncio.sleep (1)
        err == "var" and xx
        if err == "http":
            raise was.Error ("600 Error")
        return was.API (x = 100)

    @app.route ("/coro", coroutine = True)
    def c (was, err = "no"):
        task = yield was.Mask (200)
        err == "var" and xx
        if err == "http":
            raise was.Error ("600 Error")
        return was.API (x = task.fetch ())

    with app.test_client ("/", confutil.getroot (), enable_async = True) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 200
        assert resp.text == "100"

        resp = cli.get ("/api")
        assert resp.status_code == 200
        assert resp.json ()["x"] == 100

        resp = cli.get ("/coro")
        assert resp.status_code == 200
        assert resp.json ()["x"] == 200

        resp = cli.get ("/api?err=var")
        assert resp.status_code == 502
        assert "<title>502 Bad Gateway</title>" in resp.text

        resp = cli.get ("/api?err=var", headers = {"Accept": "application/json"})
        assert resp.status_code == 502
        assert "code" in resp.json ()

        resp = cli.get ("/api?err=http", headers = {"Accept": "application/json"})
        assert resp.status_code == 600
        assert "code" in resp.json ()

        resp = cli.get ("/coro?err=var")
        assert resp.status_code == 502
        assert "<title>502 Bad Gateway</title>" in resp.text

        resp = cli.get ("/coro?err=var", headers = {"Accept": "application/json"})
        assert resp.status_code == 502
        assert "code" in resp.json ()

        resp = cli.get ("/coro?err=http", headers = {"Accept": "application/json"})
        assert resp.status_code == 600
        assert "code" in resp.json ()

    assert app.hooks_called == 27