import skitai
import confutil

def test_futures (app, dbpath):
    @app.route ("/")
    def index (was):
        def response (was, rss, a):
            return was.response.API (status_code = [rs.status_code for rs in rss], a = a) 
        
        reqs = [
            was.get ("@pypi/project/skitai/"),
            was.get ("@pypi/project/rs4/"),
            was.backend ("@sqlite").execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
        ]
        return was.futures (reqs, a = 100).then (response)
    
    app.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")    
    app.alias ("@sqlite", skitai.DB_SQLITE3, dbpath)    
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.data ['status_code'] == [200, 200, 200]
        assert resp.data ['a'] == 100
        
        