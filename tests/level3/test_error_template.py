import skitai
import confutil
import pprint

def test_error_handler (app):
    @app.default_error_handler
    def default_error_handler (was, error):
        return str (error)

    @app.route ("/")
    def index (was):
        raise ValueError
    
    app.debug = True
    with app.test_client ("/", confutil.getroot ()) as cli:        
        resp = cli.get ("/")
        assert "ValueError" in resp.text
        
    app.debug = False
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert "ValueError" not in resp.text
         
        