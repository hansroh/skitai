from skitai.saddle import mounted
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
    
    testcli = mounted ("/", app, confutil.getroot ())
    
    resp = testcli.get ("/")
    assert resp.text == "Hello, World"
    
    resp = testcli.get ("/echo?m=GET")
    assert resp.text == "GET"
    
    resp = testcli.post ("/json", {"m": "POST"})
    assert resp.text == '{"data": "POST"}'
    
    resp = testcli.postjson ("/json", {"m": "POST"})
    assert resp.text == '{"data": "POST"}'
    