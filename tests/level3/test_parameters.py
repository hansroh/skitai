import skitai
import confutil
import pprint
import re

def test_parameters (app):
    @app.route ("/1/<int:id>")    
    def index1 (was):
        return "Hello"

    @app.route ("/2/<int:id>")    
    def index2 (was, id, a1 = 2):
        return "Hello"

    @app.route ("/3/<int:id>")    
    def index3 (was, id, a1):
        return "Hello"
    
    @app.route ("/4/<int:id>")    
    def index4 (was, id, **P):
        return "Hello"

    @app.route ("/5")
    def index4 (was):
        return "Hello"

    with app.test_client ("/", confutil.getroot ()) as cli:        
        resp = cli.get ("/1/1")
        assert resp.status_code == 500

        resp = cli.get ("/2/1")
        assert resp.status_code == 200

        resp = cli.get ("/3/1")
        assert resp.status_code == 400

        resp = cli.get ("/3/1?a1=2")
        assert resp.status_code == 200

        resp = cli.get ("/4/1?a1=2")
        assert resp.status_code == 200

        resp = cli.get ("/3/1?a1=2&a2=3")
        assert resp.status_code == 400

        resp = cli.get ("/5")
        assert resp.status_code == 200

        resp = cli.get ("/5?a=1")
        assert resp.status_code == 400
