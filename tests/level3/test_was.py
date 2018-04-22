from confutil import rprint, assert_request
import confutil
import skitai
import os, pytest
from skitai.server import offline

# TODO: test all was object

def test_was (wasc, app, client): 
    @app.route ("/do5/<u>")
    def index5 (was, u, a):
        return z (was)
        
    # WSGI
    vh = offline.install_vhost_handler ()
    root = confutil.getroot ()
    pref = skitai.pref ()
    vh.add_route ("default", ("/", app, root), pref)
    
    was = wasc ()
    was.app = app
    assert was.ab ("index5", "hans", "roh") == "/do5/hans?a=roh"
    
    was.request = client.get ("http://www.skitai.com/do5/hans?a=roh")
    was.request.args = {"u": "hans", "a": "roh"} 
    assert was.partial ("index5", a = "vans") == "/do5/hans?a=vans"
    
    