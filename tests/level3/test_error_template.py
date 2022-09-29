import skitai
import confutil
import pprint
import os

def test_error_handler (app):
    @app.default_error_handler
    def default_error_handler (context, error):
        return str (error)

    @app.route ("/")
    def index (context):
        raise ValueError

    os.environ ['SKITAIENV'] = 'DEVEL'
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert "ValueError" in resp.text

    os.environ ['SKITAIENV'] = 'PRODUCTION'
    app.debug = False
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert "ValueError" not in resp.text

