import skitai
import confutil
import pprint

def test_map (app, dbpath):
    @app.route ("/1")
    @app.spec (offset = int)
    def index (context, offset = 1):
        return context.API (result = offset)

    @app.route ("/2")
    def index2 (context):
        return context.route (index)

    @app.route ("/3")
    def index3 (context):
        return context.route (index, offset = 4)

    @app.route ("/4")
    def index4 (context):
        return context.route ('index', offset = 't')

    @app.route ("/5")
    @app.spec (offset = int)
    def index5 (context, offset = 1):
        return index (context, offset)

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/2")
        assert resp.status_code == 200
        assert resp.data ['result'] == 1

        resp = cli.get ("/3")
        assert resp.status_code == 200
        assert resp.data ['result'] == 4

        resp = cli.get ("/4")
        assert resp.status_code == 200
        assert resp.data ['result'] == 't'

        resp = cli.get ("/5")
        assert resp.status_code == 200
        assert resp.data ['result'] == 1

        resp = cli.get ("/5")
        assert resp.status_code == 200
        assert resp.data ['result'] == 1

        resp = cli.get ("/5?offset=5")
        assert resp.status_code == 200
        assert resp.data ['result'] == 5

        resp = cli.get ("/5?offset=z")
        assert resp.status_code == 400