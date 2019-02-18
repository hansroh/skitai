import skitai
import confutil
import pprint
import myapp 

def test_namespaced_mount (app):
    app.mount ("/v1", myapp, ns = "v1")
    app._mount (myapp)
    
    with app.test_client ("/", confutil.getroot ()) as cli:        
        resp = cli.get ("/v1/apis/owners/1")
        assert resp.status_code == 200
        assert app.urlfor ("v1.owners", 2) == "/v1/apis/owners/2"
        