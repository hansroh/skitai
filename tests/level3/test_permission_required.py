import skitai
import confutil
import pprint
import re

def test_error_handler (app):
    @app.permission_check_handler
    def permission_check_handler (was, perms):
        if perms == ["staff"]:
            return
        if perms == ["admin"]:
            return    
        return was.response ("403 Permission Denied")

    @app.route ("/")
    @app.permission_required ()
    def index (was):
        return ""
    
    @app.route ("/1")
    @app.permission_required (["staff"])
    def index1 (was):
        return ""

    @app.route ("/animals/<id>")
    @app.permission_required (id = ["admin"])
    def index2 (was, id = None):
        return ""

    with app.test_client ("/", confutil.getroot ()) as cli:        
        resp = cli.get ("/")
        assert resp.status_code == 403

        resp = cli.get ("/1")
        assert resp.status_code == 200

        resp = cli.get ("/animals")
        assert resp.status_code == 403

        resp = cli.get ("/animals/1")
        assert resp.status_code == 200
