import skitai
import confutil
import pprint
from skitai.rpc import cluster_dist_call

def test_futures (app, dbpath):
    @app.route ("/")
    def index (was):
        with was.xmlrpc ("@pypi") as stub:
            assert isinstance (stub, cluster_dist_call.Proxy)
        
        with was.db ("@sqlite") as db:            
            req = db.execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
            result = was.Tasks ([req]) [0]
        return str (result.fetch ())
    
    app.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")        
    app.alias ("@sqlite", skitai.DB_SQLITE3, dbpath)    
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert "RHAT" in resp.text
        
        