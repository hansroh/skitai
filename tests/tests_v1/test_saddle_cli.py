from skitai.saddle import Saddle
import confutil

def test_cli (app):
    @app.route ("/")
    def index (was):
        return "Hello, World"
    
    @app.route ("/echo")
    def echo (was, m):
        return m
    
    @app.route ("/json")
    def json (was, m):
        return was.response.api (data = m)
    
    mounted = app.mount ("/", confutil.getroot ())
    
    resp = mounted.get ("/")
    assert resp.text == "Hello, World"
    
    resp = mounted.get ("/echo?m=GET")
    assert resp.text == "GET"
    
    resp = mounted.post ("/json", {"m": "POST"})
    assert resp.text == '{"data": "POST"}'
    
    resp = mounted.postjson ("/json", {"m": "POST"})
    assert resp.text == '{"data": "POST"}'
    