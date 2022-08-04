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
        return context.pipe (index)

    @app.route ("/3")
    def index3 (context):
        return context.pipe (index, offset = 4)

    @app.route ("/4")
    def index4 (context):
        return context.pipe ('index', offset = 't')

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
