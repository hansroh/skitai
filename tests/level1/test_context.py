import confutil
import pytest
import skitai
import os, pytest
from skitai.testutil import offline as testutil
from atila.cookie import Cookie
from atila.named_session import NamedSession
from rs4.protocols.sock.impl.smtp import composer
import shutil
from rs4 import pathtool
import time

def test_was (Context, app, client):
    @app.route ("/do6/<u>")
    def index6 (context, u = "hansroh"):
        return z (context)

    @app.route ("/index5/<u>")
    def index5 (context, u, a, b = 3):
        return z (context)

    @app.route ("/index7/<u>")
    @app.authorization_required ("digest")
    def index7 (context, u, a, b = 3):
        return z (context)

    # WSGI
    vh = testutil.install_vhost_handler ()
    root = confutil.getroot ()
    pref = skitai.pref ()
    pref.config.MEDIA_URL = '/my/media/'
    vh.add_route ("default", ("/", app, root), pref)
    context = Context ()
    context.app = app

    with pytest.raises (AssertionError):
        assert context.static ('/index.html')
    assert context.static ('index.html') == '/static/index.html'
    assert context.media ('index.html') == '/my/media/index.html'

    for each in ("index5", "index7"):
        assert context.urlfor (each, "hans", "roh") == "/{}/hans?a=roh".format (each)
        assert context.urlfor (each, "hans", "roh") == "/{}/hans?a=roh".format (each)
        assert context.baseurl (each) == "/{}/".format (each)

        assert context.urlfor (each, "hans", "roh", b = 3) in ("/{}/hans?b=3&a=roh".format (each), "/{}/hans?a=roh&b=3".format (each))
        assert context.urlfor (each, "hans", a = "roh", b = 3) in ("/{}/hans?b=3&a=roh".format (each), "/{}/hans?a=roh&b=3".format (each))
        with pytest.raises(AssertionError):
            assert context.ab (each, b = 3)

        context.request = client.get ("http://www.skitai.com/{}/hans?a=roh".format (each))
        context.request.PARAMS = {"u": "hans"}
        context.request.URL = {"a": "roh"}
        assert context.partial (each, a = "vans") == "/{}/hans?a=vans".format (each)
        assert context.partial (each, b = 3) in ("/{}/hans?b=3&a=roh".format (each), "/{}/hans?a=roh&b=3".format (each))

    assert context.urlfor ("index6") == "/do6"
    assert context.urlfor ("index6", "jenny") == "/do6/jenny"
    assert context.urlfor ("index6", u = "jenny") == "/do6/jenny"
    context.request.args = {"u": "hans"}
    assert context.partial ("index6") == "/do6/hans"

    assert context.gentemp ().startswith ("/var/tmp")

    assert len (str (context.timestamp)) == 13
    assert len (context.uniqid) == 20

    with pytest.raises(AssertionError):
        context.session

    del context.cookie
    app.securekey = "securekey"
    assert isinstance (context.cookie, Cookie)
    assert isinstance (context.session, NamedSession)
    assert isinstance (context.mbox, NamedSession)

    assert context.txnid ().endswith ("/1000")
    assert context.tempfile.find ("skitai/__gentemp") > 0

    class Response:
        def __init__ (self, *args):
            self.args = args
    context.response = Response

    r = context.redirect ("/to")
    assert r.args [0].startswith ("302 ")
    assert r.args [1].startswith ("<html>")
    assert ('Location', '/to') in r.args [2]

    r = context.redirect ("301 Redirect", "/to")
    assert r.args [0].startswith ("301 ")
    assert r.args [1].startswith ("<html>")
    assert ('Location', '/to') in r.args [2]

    context.render ("index.html").startswith ('<!DOCTYPE html>')

    assert isinstance (context.email ("test", "a@anv.com", "b@anv.com"), composer.Composer)

    # tokens ------------------------------------------
    assert context.decode_jwt (context.encode_jwt ({"a": 1, "exp": 3000000000})) == {"a": 1, "exp": 3000000000}
    assert context.decode_jwt (context.encode_jwt ({"a": 1, "exp": 1})) == {'ecd': 0, 'err': 'token expired'}

    t = context.encode_ott ({"a": 1})
    assert context.decode_ott (t) == {"a": 1}

    t = context.encode_ott ({"a": 1}, session_key = "test")
    context.session.mount ("test")
    assert context.session ["_test_token"]
    assert context.decode_ott (t) == {"a": 1}

    context.session.mount ("test")
    context.session ["_test_token"] = 0x00
    assert context.decode_ott (t) is None
    assert context.session ["_test_token"] is None

    t = context.encode_ott ({"a": 1}, session_key = "test")
    assert context.decode_ott (t) == {"a": 1}
    context.revoke_ott (t)
    context.session.mount ("test")
    assert context.session ["_test_token"] is None
    assert context.decode_ott (t) is None

    assert context.verify_otp (context.generate_otp ())

    otp = context.generate_otp ()
    assert context.verify_otp (otp)

    time.sleep (9)
    assert context.verify_otp (otp)

    t = context.encode_ott ([1, 2])
    assert context.decode_ott (t) == [1, 2]

    t = context.csrf_token
    context.csrf_token_input.find (context.cookie [context.CSRF_NAME]) > 0

    class Request:
        args = {context.CSRF_NAME: t}
        def get_header (self, *args):
            return self.args [context.CSRF_NAME]

    context.request = Request ()

    context.request.args [context.CSRF_NAME] = 0x00
    context.request.args [context.CSRF_NAME] = t
    assert context.cookie [context.CSRF_NAME] == t
    assert context.cookie [context.CSRF_NAME]

    with pytest.raises(AttributeError):
        context.django

    salt, sig = context.encrypt_password ("111111")
    assert context.verify_password ("111111", salt, sig)

    assert len (context.make_uid ()) == 22
    assert len (context.make_uid ('234234')) == 22

    @skitai.on ("event")
    def on_event (k):
        assert k == 100
    skitai.emit ("event", 100)
