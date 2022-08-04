import skitai
import confutil
import pprint
import time

# headers = {"If-None-Match": etag}
def test_etag (app, dbpath):
    @app.route ("/1")
    def index (context):
        context.response.set_etag ('1')
        return "1"

    @app.route ("/1-1")
    def index (context):
        context.response.set_etag ('1', 60)
        return "1"

    @app.route ("/2")
    def index2 (context):
        context.response.set_mtime (1599003756, max_age = 120)
        return "1"


    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/1")
        assert resp.status_code == 200
        etag = resp.headers.get ('etag')
        assert len (etag) == len ('"c4ca4238a0b923820dcc509a6f75849b"')
        assert resp.headers.get ('content-length') == '1'

        resp = cli.get ("/1", headers = {"If-None-Match": etag})
        assert resp.status_code == 304

        resp = cli.get ("/1-1", headers = {"If-None-Match": etag})
        assert resp.status_code == 304
        assert resp.headers.get ('cache-control')

        resp = cli.get ("/2")
        assert resp.status_code == 200

        mtime = resp.headers.get ('last-modified')
        resp = cli.get ("/2", headers = {"If-Modified-Since": mtime})
        assert resp.status_code == 304
        assert resp.headers.get ('expires')
