import skitai
import confutil
import pprint

def test_db2 (app, dbpath):
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


def test_db3 (app, dbpath):
    @app.route ("/")
    def index (was):
        with was.sdb ("@sqlite") as trx:
            d = trx.execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',)).fetch ()            
        with was.sdb ("@sqlite") as trx:
            d2 = trx.execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
        return str (d2.fetch ())
            
    app.alias ("@sqlite", skitai.DB_SQLITE3, dbpath)    
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert "RHAT" in resp.text
        