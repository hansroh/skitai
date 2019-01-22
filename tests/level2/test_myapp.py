import confutil

def test_myapp ():
    from myapp import app
    
    with app.make_client ("/", approot = ".") as cli:
        # html request
        resp = cli.get ("/")
        assert "something" in resp.text
        
        # api call
        resp = cli.apis.pets ("45").get ()
        assert "id" in resp.data
        
        