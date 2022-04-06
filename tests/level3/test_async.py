import asyncio
import confutil
import json
import time

def test_success (app):
    app.hooks_called = 0
    app.fired = 0

    @app.on ("FIRE")
    async def on_FIRE (was):
        app.fired += 1

    @app.before_request
    async def before_request (was):
        app.hooks_called += 1

    @app.failed_request
    async def failed_request (was, expt):
        app.hooks_called += 1

    @app.finish_request
    async def finish_request (was):
        app.hooks_called += 1

    @app.teardown_request
    async def teardown_request (was):
        app.hooks_called += 1

    @app.route ("/")
    async def a (was):
        app.emit ("FIRE")
        await was.to_thread (time.sleep, 1)
        await was.to_process (time.sleep, 1)
        await asyncio.sleep (1)
        return "100"

    @app.route ("/api")
    async def b (was, err = "no"):
        app.emit ("FIRE")
        await asyncio.sleep (1)
        err == "var" and xx
        if err == "http":
            raise was.Error ("600 Error")
        return was.API (x = 100)

    @app.route ("/coro", coroutine = True)
    def c (was, err = "no"):
        app.emit ("FIRE")
        task = yield was.Mask (200)
        err == "var" and xx
        if err == "http":
            raise was.Error ("600 Error")
        return was.API (x = task.fetch ())

    N = 3
    with app.test_client ("/", confutil.getroot (), enable_async = True) as cli:
        for _ in range (N):
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

    assert app.hooks_called == 27 * N
    assert app.fired == 9 * N