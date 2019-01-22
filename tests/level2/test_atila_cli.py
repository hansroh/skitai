from atila import Atila
import confutil
import skitai
import asyncore
import os

def test_cli (app, dbpath):
    @app.route ("/")
    def index (was):
        return "Hello, World"
    
    @app.route ("/echo")
    def echo (was, m):
        return m
    
    @app.route ("/json")
    def json (was, m):
        return was.response.api (data = m)
    
    @app.route ("/pypi")
    def pypi (was):
        req = was.get ("@pypi/project/skitai/")
        res = req.getwait ()
        return was.response.api (data = res.text)
    
    @app.route ("/pypi2")
    def pypi2 (was):
        req = was.get ("https://pypi.org/project/skitai/")
        res = req.getwait ()
        return was.response.api (data = res.text)
    
    @app.route ("/db")
    def db (was):
        stub = was.backend ("@sqlite")
        req = stub.execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
        res = req.getwait ()
        return was.response.api (data = res.data)
    
    app.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")    
    app.alias ("@sqlite", skitai.DB_SQLITE3, dbpath)
    with app.make_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.text == "Hello, World"

        resp = cli.get ("/echo?m=GET")
        assert resp.text == "GET"
        
        resp = cli.post ("/json", {"m": "POST"})
        assert resp.text == '{"data": "POST"}'
        
        resp = cli.postjson ("/json", {"m": "POST"})
        assert resp.text == '{"data": "POST"}'
        
        resp = cli.get ("/db")
        assert resp.data ["data"][0][2] == 'RHAT'
        
        resp = cli.get ("/pypi2")
        assert "skitai" in resp.text
        
        resp = cli.get ("/pypi")
        assert "skitai" in resp.text
        