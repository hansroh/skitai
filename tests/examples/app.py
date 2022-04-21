import os
from atila import Atila
import skitai
from services import sub
import time
import sys
is_pypy = '__pypy__' in sys.builtin_module_names

if os.name == "nt":
    from rs4.psutil.win32service import ServiceFramework
    class ServiceConfig (ServiceFramework):
        _svc_name_ = "SAE_EXAMPLE"
        _svc_display_name_ = "Skitai Example Service"
        _svc_app_ = __file__
        _svc_python_ = r"c:\python34\python.exe"

app = Atila (__name__)
app.debug = True
app.use_reloader = True
app.jinja_overlay ()


app.realm = "Secured Area"
app.users = {"admin": ("1111", 0, {'role': 'root'})}
app.authenticate = None

app.mount ("/sub", sub)

@app.route ("/")
def index (was):
    return was.render ("index.html")

@app.route ("/response_chain")
def response_chain (was):
    def respond2 (was, task):
        return was.API (status_code = task.dispatch ().status_code)
    def respond (was, task):
        return was.Mask ("pypi/skitai/hansroh/rs4").then (respond2)
    return was.Mask ("pypi/skitai/hansroh/rs4").then (respond)

@app.route ("/dnserror")
def dnserror (was):
    req = was.Mask ("pypi/skitai/hansroh/rs4")
    rs = req.dispatch (timeout = 10)
    return "%d %d %s" % (rs.status, rs.status_code, rs.reason)

@app.route ("/xmlrpc")
def xmlrpc (was):
    return was.API (result = "ok")

@app.route ("/hello")
def hello (was, num = 1):
    was.response ["Content-Type"] = "text/plain"
    return "\n".join (["hello" for i in range (int(num))])

@app.route ("/redirect0")
def redirect0 (was):
    return ""

@app.route ("/redirect1")
def redirect1 (was):
    return was.response ("301 Object Moved", "", headers = [("Location", "/redirect2")])

@app.route ("/redirect2")
def redirect2 (was):
    return was.response ("301 Object Moved", "", headers = [("Location", "/")])

@app.route ("/upload")
def upload (was, **karg):
    return was.response ("200 OK", str (karg), headers = [("Content-Type", "text/plain")])

@app.route ("/upload2")
def upload2 (was, **form):
    return str (list (form.keys ()))

@app.route ("/post")
def post (was, username):
    return 'USER: %s' % username

@app.route ("/test")
def test (was):
    was.response ["Content-Type"] = "text/plain"
    return str (was.request.args)

@app.route ("/json")
def json (was):
    return was.response.api (data = "JSON")

@app.route ("/promise")
def promise (was):
    was.push (was.ab (hello))
    was.push (was.ab (test))
    return was.response.api (data = "JSON")

@app.route ("/delay")
def delay (was, wait = 3):
    time.sleep (float (wait))
    return was.response.api (data = "JSON")

@app.route ("/shutdown")
def shutdown (was, stream_id = 1):
    was.request.protocol.close (last_stream_id = int (stream_id))
    return 'CLOSED'

@app.route ("/nchar")
@app.require (ints = ['n'])
def nchar (was, n = 167357):
    return 'a' * n

@app.route ("/mixing")
def mixing (was):
    def respond (was, tasks):
        a, b, c, d, e, f = tasks.fetch ()
        return was.API (a =a, b = b, c = c, d = d, e = e, f = f)
    return was.Tasks (
        was.Mask ([]),
        was.Mask ("pypi/skitai/hansroh/rs4"),
        was.Thread (time.sleep, args = (0.3,)),
        was.Process (time.sleep, args = (0.3,)),
        was.Mask ('mask'),
        was.Subprocess ("ls"),
    ).then (respond)


if __name__ == "__main__":
    import skitai

    if os.name == "nt":
        skitai.set_service (ServiceConfig)

    skitai.mount ("/", 'statics')
    with skitai.preference () as pref:
        pref.config.MAX_UPLOAD_SIZE = 20 * 1024 * 1024
        skitai.mount ("/", app, pref)
        skitai.mount ("/websocket", 'websocket.py')
        skitai.mount ("/rpc2", 'rpc2.py')
        skitai.mount ("/routeguide.RouteGuide", 'grpc_route_guide.py')
        skitai.mount ("/members", 'auth.py')

    skitai.run (
        port = 30371,
        workers = 1,
        threads = 4
    )
