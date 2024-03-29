import skitai
import confutil
import pprint
from io import BytesIO

def test_futures (app, dbpath):
    @app.route ("/")
    def index (context):
        return context.File (__file__, 'application/python', 'test.py')

    @app.route ("/1")
    def index2 (context):
        f = BytesIO ()
        f.write (b'Be cool')
        return context.File (f, 'application/python', 'test.py')

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 200
        assert resp.headers.get ('content-type') == 'application/python'
        assert b'application/python' in resp.content

        resp = cli.get ("/1")
        print (resp.headers)
        assert resp.status_code == 200
        assert resp.headers.get ('content-type') == 'application/python'
        assert 'Be cool' in resp.text

