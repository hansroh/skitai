import skitai
import confutil
import pprint

def test_websocket (app):
    def onopen (was):
        return  'Welcome'

    @app.route ("/echo")
    @app.websocket (skitai.WS_CHANNEL, 60, onopen = onopen)
    def echo (was, message):
        was.websocket.send ('1st: ' + message)
        return "2nd: " + message

    @app.route ("/echo2")
    @app.websocket (skitai.WS_CHANNEL | skitai.WS_NOTHREAD, 60, onopen = onopen)
    def echo2 (was, message):
        was.websocket.send ('1st: ' + message)
        return "2nd: " + message

    @app.route ("/echo3")
    @app.websocket (skitai.WS_CHANNEL | skitai.WS_SESSION, 60)
    def echo3 (was):
        yield '111'

    app.access_control_allow_origin = ["http://sada.com"]
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.ws ("/echo", "hello")
        assert resp.status_code == 403

    app.access_control_allow_origin = ["*"]
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.ws ("/echo", "hello")
        assert resp.status_code == 101
        assert resp.content == b'\x81\x07Welcome'

        resp = cli.ws ("/echo2", "hello2")
        assert resp.status_code == 101
        assert resp.content == b'\x81\x07Welcome'

        resp = cli.ws ("/echo3", "hello3")
        assert resp.status_code == 101
        assert resp.content == b''

