import skitai
import confutil
import pprint

def test_map (app, dbpath):
    @app.route ("/1", subdomain = 'k')
    @app.spec (offset = int)
    def index (was, offset = 1):
        return was.API (result = offset)

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/1")
        assert resp.status_code == 404

        resp = cli.get ("/1", headers = {'Host': 'kk.localhost'})
        assert resp.status_code == 404

        resp = cli.get ("/1", headers = {'Host': 'k.localhost'})
        assert resp.status_code == 200
