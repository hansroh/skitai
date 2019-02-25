import skitai
import confutil
import pprint

def test_futures (app, dbpath):
    @app.route ("/")
    def index (was):
        with was.transaction ("@sqlite") as trx:
            trx.execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
            d = trx.fetchall ()
        
        with was.transaction ("@sqlite") as trx:
            trx.execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
            d = trx.fetchall ()
                
        return str (d)
            
    app.alias ("@sqlite", skitai.DB_SQLITE3, dbpath)    
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert "RHAT" in resp.text
        