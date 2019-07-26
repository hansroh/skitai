import skitai
import confutil
import pprint
import re

def test_error_handler (app):
    @app.route ("/a")
    @app.parameters_required ("JSON", ["limit"])
    def indexa (was, limit):
        return was.API ()

    @app.route ("/b")
    @app.parameters_required ("URL", ["limit"])
    def indexb (was, limit):
        raise was.Error ("422 Bad Request")    

    with app.test_client ("/", confutil.getroot ()) as cli:    
        app.expose_spec = True
        app.debug = True   
        resp = cli.api ().a.post ({"limit": 10})
        assert resp.status_code == 200
        assert "__spec__" in resp.data

        resp = cli.api ().b.get (limit = 10)
        assert resp.status_code == 422
        assert "__spec__" in resp.data

        app.debug = False
        app.expose_spec = False

        
