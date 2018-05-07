from confutil import rprint, assert_request
import confutil
import pytest
import skitai
import os, pytest
from skitai.server import offline
from skitai.server.wastuff.promise import _Method
from skitai.saddle.cookie import Cookie
from skitai.saddle.named_session import NamedSession
from aquests.protocols.smtp import composer
import shutil
from aquests.lib import pathtool
from sqlphile.sqlmap import SQLMap

def test_was (wasc, app, client): 
    @app.route ("/do5/<u>")
    def index5 (was, u, a, b = 3):
        return z (was)
    
    @app.route ("/do6/<u>")
    def index6 (was, u = "hansroh"):
        return z (was)
        
    # WSGI
    vh = offline.install_vhost_handler ()
    root = confutil.getroot ()
    pref = skitai.pref ()
    vh.add_route ("default", ("/", app, root), pref)
    was = wasc ()
    was.app = app
    
    assert was.urlfor ("index5", "hans", "roh") == "/do5/hans?a=roh"
    assert was.urlfor ("index5", "hans", "roh") == "/do5/hans?a=roh"
    assert was.baseurl ("index5") == "/do5/"
    
    assert was.urlfor ("index5", "hans", "roh", b = 3) in ("/do5/hans?b=3&a=roh", "/do5/hans?a=roh&b=3")
    assert was.urlfor ("index5", "hans", a = "roh", b = 3) in ("/do5/hans?b=3&a=roh", "/do5/hans?a=roh&b=3")
    with pytest.raises(AssertionError):
        assert was.ab ("index5", b = 3)
    
    assert was.urlfor ("index6") == "/do6/hansroh"
    assert was.urlfor ("index6", "jenny") == "/do6/jenny"
    assert was.urlfor ("index6", u = "jenny") == "/do6/jenny"
    
    was.request = client.get ("http://www.skitai.com/do5/hans?a=roh")
    was.request.args = {"u": "hans", "a": "roh"} 
    assert was.partial ("index5", a = "vans") == "/do5/hans?a=vans"
    assert was.partial ("index5", b = 3) in ("/do5/hans?b=3&a=roh", "/do5/hans?a=roh&b=3")
    
    assert was.gentemp ().startswith ("/var/tmp")
    
    was.add_cluster (skitai.PROTO_HTTP, "@test", "127.0.0.1:5000")
    assert "@test" in was.clusters_for_distcall
    
    was.add_cluster (skitai.PROTO_HTTP, "@test-1", "127.0.0.1:5000 10")
    assert "@test-1" in was.clusters_for_distcall
    
    was.add_cluster (skitai.PROTO_HTTP, "@test-1", ["127.0.0.1:5000 10"])
    assert "@test-1" in was.clusters_for_distcall
        
    assert len (str (was.timestamp)) == 13
    assert len (was.uniqid) == 20
    
    assert type (was._clone ()) is type (was)
    assert not was._clone (True).VALID_COMMANDS
    
    for each in was.VALID_COMMANDS:
        assert isinstance (eval ("was." + each), _Method)
        assert isinstance (eval ("was." + each + ".lb"), _Method)
        assert isinstance (eval ("was." + each + ".map"), _Method)
    
    with pytest.raises(AssertionError):
        was.session
    
    del was.cookie
    app.securekey = "securekey"
    assert isinstance (was.cookie, Cookie)    
    assert isinstance (was.session, NamedSession)
    assert isinstance (was.mbox, NamedSession)
        
    assert was.txnid ().endswith ("/1000")
    assert was.rebuild_header () ["X-Ltxn-Id"] == "1001"
    x = was.rebuild_header ({"a": "b"})
    assert "a" in x
    assert x ["X-Ltxn-Id"] == "1002"
    x = was.rebuild_header ([("a", "b")])
    assert "a" in x
    assert x ["X-Ltxn-Id"] == "1003"    
    assert was.tempfile.find ("skitai-gentemp") > 0
    
    class Response:
        def __init__ (self, *args):
            self.args = args            
    was.response = Response
    r = was.redirect ("/to")
    assert r.args [0].startswith ("302 ")
    assert r.args [1].startswith ("<html>")
    assert ('Location', '/to') in r.args [2]
    was.render ("index.html").startswith ('<!DOCTYPE html>')
    
    assert isinstance (was.email ("test", "a@anv.com", "b@anv.com"), composer.Composer)
    
    # tokens ------------------------------------------    
    assert was.dejwt (was.mkjwt ({"a": 1})) == {"a": 1}
    
    t = was.mktoken ({"a": 1})
    assert was.detoken (t) == {"a": 1}
    
    t = was.mktoken ({"a": 1}, session_key = "test")
    assert was.session ["_test_token"]    
    assert was.detoken (t) == {"a": 1}
    
    was.session ["_test_token"] = 0x00
    assert was.detoken (t) is None
    assert was.session ["_test_token"] is None
    
    t = was.mktoken ({"a": 1}, session_key = "test")
    assert was.detoken (t) == {"a": 1}
    was.rmtoken (t)
    assert was.session ["_test_token"] is None
    assert was.detoken (t) is None
    
    t = was.mktoken ([1, 2])
    assert was.detoken (t) == [1, 2]
    
    t = was.csrf_token
    was.csrf_token_input.find (was.session [was.CSRF_NAME]) > 0
    
    class Request:
        args = {was.CSRF_NAME: t}
    
    was.request = Request
    
    was.request.args [was.CSRF_NAME] = 0x00
    assert not was.csrf_verify (True)    
    was.request.args [was.CSRF_NAME] = t
    assert was.csrf_verify (True)
    assert was.session [was.CSRF_NAME] == t
    
    assert was.csrf_verify ()
    assert was.session [was.CSRF_NAME] is None
    
    assert isinstance (was.sql, SQLMap)
    with pytest.raises(AttributeError):
        was.django

    