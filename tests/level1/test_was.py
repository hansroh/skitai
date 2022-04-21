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

def test_was (wasc, app, client):
    @app.route ("/do6/<u>")
    def index6 (was, u = "hansroh"):
        return z (was)

    @app.route ("/index5/<u>")
    def index5 (was, u, a, b = 3):
        return z (was)

    @app.route ("/index7/<u>")
    @app.authorization_required ("digest")
    def index7 (was, u, a, b = 3):
        return z (was)

    # WSGI
    vh = testutil.install_vhost_handler ()
    root = confutil.getroot ()
    pref = skitai.pref ()
    pref.config.MEDIA_URL = '/my/media/'
    vh.add_route ("default", ("/", app, root), pref)
    was = wasc ()
    was.app = app

    with pytest.raises (AssertionError):
        assert was.static ('/index.html')
    assert was.static ('index.html') == '/static/index.html'
    assert was.media ('index.html') == '/my/media/index.html'

    for each in ("index5", "index7"):
        assert was.urlfor (each, "hans", "roh") == "/{}/hans?a=roh".format (each)
        assert was.urlfor (each, "hans", "roh") == "/{}/hans?a=roh".format (each)
        assert was.baseurl (each) == "/{}/".format (each)

        assert was.urlfor (each, "hans", "roh", b = 3) in ("/{}/hans?b=3&a=roh".format (each), "/{}/hans?a=roh&b=3".format (each))
        assert was.urlfor (each, "hans", a = "roh", b = 3) in ("/{}/hans?b=3&a=roh".format (each), "/{}/hans?a=roh&b=3".format (each))
        with pytest.raises(AssertionError):
            assert was.ab (each, b = 3)

        was.request = client.get ("http://www.skitai.com/{}/hans?a=roh".format (each))
        was.request.PARAMS = {"u": "hans"}
        was.request.URL = {"a": "roh"}
        assert was.partial (each, a = "vans") == "/{}/hans?a=vans".format (each)
        assert was.partial (each, b = 3) in ("/{}/hans?b=3&a=roh".format (each), "/{}/hans?a=roh&b=3".format (each))

    assert was.urlfor ("index6") == "/do6"
    assert was.urlfor ("index6", "jenny") == "/do6/jenny"
    assert was.urlfor ("index6", u = "jenny") == "/do6/jenny"
    was.request.args = {"u": "hans"}
    assert was.partial ("index6") == "/do6/hans"

    assert was.gentemp ().startswith ("/var/tmp")

    assert len (str (was.timestamp)) == 13
    assert len (was.uniqid) == 20

    with pytest.raises(AssertionError):
        was.session

    del was.cookie
    app.securekey = "securekey"
    assert isinstance (was.cookie, Cookie)
    assert isinstance (was.session, NamedSession)
    assert isinstance (was.mbox, NamedSession)

    assert was.txnid ().endswith ("/1000")
    assert was.tempfile.find ("skitai/__gentemp") > 0

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
    assert was.decode_jwt (was.encode_jwt ({"a": 1, "exp": 3000000000})) == {"a": 1, "exp": 3000000000}
    assert was.decode_jwt (was.encode_jwt ({"a": 1, "exp": 1})) == {'ecd': 0, 'err': 'token expired'}

    t = was.encode_ott ({"a": 1})
    assert was.decode_ott (t) == {"a": 1}

    t = was.encode_ott ({"a": 1}, session_key = "test")
    was.session.mount ("test")
    assert was.session ["_test_token"]
    assert was.decode_ott (t) == {"a": 1}

    was.session.mount ("test")
    was.session ["_test_token"] = 0x00
    assert was.decode_ott (t) is None
    assert was.session ["_test_token"] is None

    t = was.encode_ott ({"a": 1}, session_key = "test")
    assert was.decode_ott (t) == {"a": 1}
    was.revoke_ott (t)
    was.session.mount ("test")
    assert was.session ["_test_token"] is None
    assert was.decode_ott (t) is None

    assert was.verify_otp (was.generate_otp ())

    otp = was.generate_otp ()
    assert was.verify_otp (otp)

    time.sleep (9)
    assert was.verify_otp (otp)

    t = was.encode_ott ([1, 2])
    assert was.decode_ott (t) == [1, 2]

    t = was.csrf_token
    was.csrf_token_input.find (was.cookie [was.CSRF_NAME]) > 0

    class Request:
        args = {was.CSRF_NAME: t}
        def get_header (self, *args):
            return self.args [was.CSRF_NAME]

    was.request = Request ()

    was.request.args [was.CSRF_NAME] = 0x00
    was.request.args [was.CSRF_NAME] = t
    assert was.cookie [was.CSRF_NAME] == t
    assert was.cookie [was.CSRF_NAME]

    with pytest.raises(AttributeError):
        was.django

    salt, sig = was.encrypt_password ("111111")
    assert was.verify_password ("111111", salt, sig)

    assert len (was.make_uid ()) == 22
    assert len (was.make_uid ('234234')) == 22


