from atila import Atila
import confutil
import skitai
import asyncore
import os
from rs4 import jwt as jwt_
import time

def test_cli (app, dbpath):
    @app.route ("/hello")
    @app.route ("/")
    def index (was):
        return "Hello, World"
    
    @app.route ("/petse/<int:id>")
    def pets_error (was):
        return "Pets"
    
    @app.route ("/pets/<int:id>", methods = ["GET", "POST"])
    def pets (was, id = None):
        return "Pets{}".format (id)
    
    @app.route ("/pets2/<int:id>", methods = ["POST"])
    def pets2 (was, id = None):
        return "Pets{}".format (id)
    
    @app.route ("/pets3/<int:id>")
    def pets3 (was, id = None):
        return "Pets{}".format (id)
    
    @app.route ("/echo")
    def echo (was, m):
        return m
    
    @app.route ("/json")
    def json (was, m):
        return was.response.api (data = m)
    
    @app.route ("/pypi")
    def pypi (was):
        req = was.get ("@pypi/project/skitai/")
        res = req.dispatch ()
        return was.response.api (data = res.text)
    
    @app.route ("/pypi3")
    def pypi3 (was):
        req = was.getjson ("https://pypi.org/project/skitai/")
        res = req.dispatch ()
        return was.response.api (data = res.text)
    
    @app.route ("/pypi2")
    def pypi2 (was):
        req = was.get ("https://pypi.org/project/skitai/")
        res = req.dispatch ()
        return was.response.api (data = res.text)
    
    @app.route ("/db")
    def db (was):
        stub = was.backend ("@sqlite")
        req = stub.execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
        res = req.dispatch ()
        return was.response.api (data = res.data)
    
    @app.route ('/jwt')
    @app.authorization_required ("bearer")
    def jwt (was):
        return was.response.api (was.request.JWT)
    
    @app.route ("/db2")
    def db2 (was):
        stub = was.backend ("@sqlite")
        req = stub.select ("stocks").filter (symbol = 'RHAT').execute ()
        res = req.dispatch ()
        return was.response.api (data = res.data)
    
    @app.maintain
    def increase (was, now, count):
        if "total-user" in app.store:
            app.store.set ("total-user", app.store.get ("total-user") + 100)        
        
    @app.route ("/getval")
    def getval (was):
        ret = str (app.store.get ("total-user"))
        return ret
        
    app.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")    
    app.alias ("@sqlite", skitai.DB_SQLITE3, dbpath)
    app.alias ("@postgres", skitai.DB_POSTGRESQL, "postgres:password@192.168.0.80/coin_core")
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.text == "Hello, World"
        
        resp = cli.get ("/hello")
        assert resp.text == "Hello, World"
        
        resp = cli.get ("/petse/1")
        assert resp.status_code == 530
        
        resp = cli.get ("/pets/1")
        assert resp.status_code == 200
        assert resp.text == "Pets1"
        
        resp = cli.post ("/pets", {"a": 1})
        assert resp.status_code == 200
        assert resp.text == "PetsNone"
        
        resp = cli.get ("/pets")
        assert resp.status_code == 200        
        
        resp = cli.get ("/pets2/1")
        assert resp.status_code == 405
        
        resp = cli.post ("/pets2/1", {"id": 1})
        assert resp.status_code == 200        
        
        resp = cli.post ("/pets2", {"a": 1})
        assert resp.status_code == 200
        assert resp.text == "PetsNone"
        
        resp = cli.get ("/pets2")
        assert resp.status_code == 405
        
        resp = cli.get ("/pets3")
        assert resp.text == "PetsNone"
        
        resp = cli.get ("/pets3/1")
        print (resp)
        assert resp.text == "Pets1"
        
        resp = cli.get ("/echo?m=GET")
        assert resp.text == "GET"
        
        resp = cli.post ("/json", {"m": "POST"})
        assert '"data": "POST"' in resp.text
        
        resp = cli.post ("/json", {"m": "POST"})
        assert '"data": "POST"' in resp.text
    
        resp = cli.get ("/db2")
        assert resp.data ["data"][0][3] == 'RHAT'
        
        resp = cli.get ("/db")
        assert resp.data ["data"][0][3] == 'RHAT'
        
        resp = cli.get ("/pypi3")
        assert resp.status_code == 502
        
        resp = cli.get ("/pypi2")
        assert "skitai" in resp.text
        
        resp = cli.get ("/pypi")
        assert "skitai" in resp.text
        
        app.securekey = "securekey"        
        resp = cli.get ("/jwt", headers = {"Authorization": "Bearer {}".format (jwt_.gen_token (app.salt, {"exp": 3000000000, "username": "hansroh"}))})
        assert resp.data == {'exp': 3000000000, 'username': 'hansroh'}
        
        resp = cli.get ("/jwt", headers = {"Authorization": "Bearer {}".format (jwt_.gen_token (app.salt, {"exp": 1, "username": "hansroh"}))})
        assert resp.code == 401
        assert resp.get_header ("WWW-Authenticate") == 'Bearer realm="App", error="token expired"'
        app.securekey = None
        
        app.config.maintain_interval = 1
        app.store.set ("total-user", 100)
        time.sleep (2)
        resp = cli.get ("/getval")
        assert int (resp.text) >= 200
        
        
        