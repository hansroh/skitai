import asyncio
import confutil

def test_events (wasc, app):
    @app.route ("/")
    async def b (was):
        await asyncio.sleep (1)
        return "100"

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")

        # assert resp.text == "100"
