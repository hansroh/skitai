import skitai
import confutil
import pprint

def test_futures (app, dbpath):
    @app.route ("/")
    def index (was):
        def respond (was, rss, a):
            return was.response.API (status_code = [rs.status_code for rs in rss], a = a) 
        
        reqs = [
            was.get ("@pypi/project/skitai/"),
            was.get ("@pypi/project/rs4/"),
            was.backend ("@sqlite").execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
        ]
        return was.futures (reqs).then (respond, a = 100)
    
    @app.route ("/2")
    def index2 (was):
        def repond (was, rss, b, status_code):
            return was.response.API (status_code_db = [rs.status_code for rs in rss], b = b, status_code = status_code) 
        
        def checkdb (was, rss, a):
            reqs = [was.backend ("@sqlite").execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))]
            return was.futures (reqs).then (repond, b = a + 100, status_code = [rs.status_code for rs in rss])
        
        def begin ():
            reqs = [
                was.get ("@pypi/project/skitai/"),
                was.get ("@pypi/project/rs4/")            
            ]
            return was.futures (reqs).then (checkdb, a = 100)
        begin ()
        
    app.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")    
    app.alias ("@sqlite", skitai.DB_SQLITE3, dbpath)    
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.data ['status_code'] == [200, 200, 200]
        assert resp.data ['a'] == 100
        
        resp = cli.get ("/2")
        assert resp.data ['status_code'] == [200, 200]
        assert resp.data ['status_code_db'] == [200]
        assert resp.data ['b'] == 200
        
        pprint.pprint (resp.data)
        