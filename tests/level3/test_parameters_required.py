import skitai
import confutil
import pprint

def test_error_handler (app):
    @app.route ("/")
    @app.parameters_required ("URL", ["limit"])
    def index (was):
        return ""
    
    @app.route ("/2")
    @app.parameters_required ("FORM", ["limit"])
    def index2 (was):
        return ""
    
    @app.route ("/3")
    @app.parameters_required ("JSON", ["limit"])
    def index3 (was):
        return ""
    
    @app.route ("/4")
    @app.parameters_required ("ARGS", ["limit"])
    def index4 (was):
        return ""
    
    with app.test_client ("/", confutil.getroot ()) as cli:        
        resp = cli.get ("/")
        assert resp.status_code == 400
         
        resp = cli.get ("/?limit=4")
        assert resp.status_code == 200
        
        resp = cli.get ("/2?limit=4")
        assert resp.status_code == 400
        
        resp = cli.post ("/2", {"limit": 4})
        assert resp.status_code == 200
        
        api = cli.api ()
        resp = api ("2").post ({"limit": 4})
        assert resp.status_code == 400
        
        api = cli.api ()
        resp = api ("3").post ({"limit": 4})
        assert resp.status_code == 200
        
        api = cli.api ()
        resp = api ("4").post ({"limit": 4})
        assert resp.status_code == 200
        
        resp = cli.get ("/4?limit=4")
        assert resp.status_code == 200
        
        resp = cli.post ("/4", {"limit": 4})
        assert resp.status_code == 200
        
        