import skitai
import confutil
import pprint
import json

def test_default_error_handler (app):
    @app.default_error_handler
    def default_error_handler (context, error):
        context.response.update ("Content-Type", "application/json; charset: utf8")
        error ["say"] = "hello"
        return json.dumps (error, ensure_ascii = False, indent = 2)

    @app.route ("/f1")
    def f1 (context):
        def respond (context, rss):
            raise context.HttpError ("414 Not Found")
        reqs = [context.Mask ("@pypi/project/rs4/")]
        return context.Tasks (reqs).then (respond)

    @app.route ("/f2")
    def f2 (context):
        raise context.HttpError ("414 Not Found")

    with app.test_client ("/", confutil.getroot ()) as cli:
        api = cli.api ("/")
        resp = api.f1.get ()
        assert resp.status_code == 414
        assert resp.data ["say"] == "hello"

        resp = api.f2.get ()
        assert resp.status_code == 414
        assert resp.data ["say"] == "hello"

        assert resp.get_header ("content-type") == "application/json; charset: utf8"
