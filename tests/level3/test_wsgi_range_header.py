import skitai
import confutil
import pprint
import re


def test_wsgi_range_header (app):
    @app.route ("/")
    def index (context):
        return "Hello"

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 200
        assert resp.text == 'Hello'

        resp = cli.get ("/", headers = {'Range': 'bytes=0,3'})
        assert resp.status_code == 416

        resp = cli.get ("/", headers = {'Range': 'bytes=100-'})
        assert resp.status_code == 416

        resp = cli.get ("/", headers = {'Range': 'bytes=0-3'})
        assert resp.status_code == 206
        assert resp.text == 'Hell'