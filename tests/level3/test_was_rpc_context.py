import skitai
import confutil
import pprint
from xmlrpc.client import ServerProxy

def test_futures (app, dbpath):
    @app.route ("/")
    def index (context):
        req = context.Mask ([{'id': 1, 'symbol': 'RHAT'}, {'id': 2, 'symbol': 'RHAT'}])
        result = context.Tasks ([req]) [0]
        return str (result.fetch ())

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert "RHAT" in resp.text

