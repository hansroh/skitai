import skitai
import confutil
import pprint
import re

def test_error_handler (app):
    @app.permission_check_handler
    def permission_check_handler (was, perms):
        if not perms:
            return
        if "admin" in perms:
            raise was.Error ("402 Permission Denied")
        raise was.Error ("403 Permission Denied")

    @app.route ("/")
    @app.permission_required ()
    def index (was):
        return ""
    
    @app.route ("/1")
    @app.permission_required (["staff"])
    def index1 (was):
        return ""

    @app.route ("/animals/<int:id>", methods = ["GET", "DELETE"])
    @app.permission_required (id = ["staff"], DELETE = ["admin"])
    def index2 (was, id = None):
        return ""

    @app.route ("/animals2/<int:id>", methods = ["GET", "DELETE", "PATCH"])
    @app.permission_required (id = ["staff"])
    def index3 (was, id = None):
        return ""

    with app.test_client ("/", confutil.getroot ()) as cli:        
        resp = cli.get ("/")
        assert resp.status_code == 200

        resp = cli.get ("/1")
        assert resp.status_code == 403

        resp = cli.get ("/animals")
        assert resp.status_code == 200

        resp = cli.get ("/animals/me")
        assert resp.status_code == 200

        resp = cli.get ("/animals/1")
        assert resp.status_code == 403

        resp = cli.delete ("/animals/1")
        assert resp.status_code == 402
        
        resp = cli.get ("/animals2/them")
        assert resp.status_code == 404

        resp = cli.get ("/animals2/me")
        assert resp.status_code == 200

        resp = cli.get ("/animals2/notme")
        assert resp.status_code == 403

        resp = cli.delete ("/animals2/notme")
        assert resp.status_code == 421

        resp = cli.patch ("/animals2/notme", {})
        assert resp.status_code == 421