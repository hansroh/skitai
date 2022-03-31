import asyncio
import confutil
import json

def test_events (app):
    @app.route ("/")
    async def a (was):
        await asyncio.sleep (1)
        return "100"

    @app.route ("/api")
    async def b (was):
        await asyncio.sleep (1)
        return was.API (x = 100)

    with app.test_client ("/", confutil.getroot (), enable_async = True) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 200
        assert resp.text == "100"

        resp = cli.get ("/api")
        assert resp.status_code == 200
        assert resp.json ()["x"] == 100

