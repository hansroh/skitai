import skitai
import confutil
import pprint
from xmlrpc.client import ServerProxy

def test_futures (app, dbpath):
    @app.route ("/")
    def index (was):
        with was.xmlrpc ("@pypi/pypi") as stub:
            req = stub.package_releases ('roundup')
            assert req.fetch () == ['2.1.0']

        req = was.Mask ([{'id': 1, 'symbol': 'RHAT'}, {'id': 2, 'symbol': 'RHAT'}])
        result = was.Tasks ([req]) [0]
        return str (result.fetch ())

    app.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert "RHAT" in resp.text

