import confutil

def test_myapp ():
    from myapp import app

    with app.test_client ("/", approot = ".") as cli:
        # html request
        resp = cli.get ("/")
        assert "something" in resp.text

        # api call
        resp = cli.api ().apis.pets ("45").get ()
        assert "id" in resp.data

        #resp = cli.api ().apis.context.get ()
        #assert resp.data['a'] and not resp.data ['b']

