import os
from atila import Atila
import skitai
from services import sub
from skitai import was as cwas

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

@app.route ("/dnserror")
def dnserror (was):
    req = was.get ("https://pypi.python.orgx/pypi/skitai", headers = (["Accept", "text/html"]))
    rs = req.dispatch (timeout = 10)
    return "%d %d %s" % (rs.status, rs.status_code, rs.reason)

@app.route ("/documentation")
def documentation (was):
    req = was.get ("https://pypi.org/project/skitai/", headers = [("Accept", "text/html")])
    pypi_content = "<h4><p>It seems some problem at <a href='https://pypi.python.org/pypi/skitai'>PyPi</a>.</p></h4><p>Please visit <a href='https://pypi.python.org/pypi/skitai'> https://pypi.python.org/pypi/skitai</a></p>"
    rs = req.dispatch (timeout = 10, cache = 60)
    if rs.data:
        content = rs.data
        s = content.find ('<div class="project-description">')
        if s != -1:
            e = content.find ('<div id="history"', s)
            if e != -1:
                pypi_content = "<h4>This contents retrieved right now using skitai was service from <a href='https://pypi.python.org/pypi/skitai'> https://pypi.python.org/pypi/skitai</a></h4>" + content [s:e]
    return was.render ("documentation.html", content = pypi_content)

@app.route ("/documentation2")
def documentation2 (was):
    def response (was, rss):
        rs = rss [0]
        pypi_content = "<h3>Error</h3>"
        if rs.data:
            content = rs.data
            s = content.find ('<div class="project-description">')
            if s != -1:
                e = content.find ('<div id="history"', s)
                if e != -1:
                    content = "<h4>This contents retrieved right now using skitai was service from <a href='https://pypi.org/project/skitai/'> https://pypi.org/project/skitai/</a></h4>" + content [s:e]
        assert "Internet :: WWW/HTTP" in content
        return was.render ("documentation2.html", skitai = content)

    reqs = [was.get ("@pypi/project/aquests/", headers = [("Accept", "text/html")])]
    return was.futures (reqs).then (response)

@app.route ("/documentation3")
def documentation3 (was):
    def response (was, rss):
        return was.response.API (status_code = [rs.status_code for rs in rss.dispatch ()])

    reqs = [
        was.get ("@pypi/project/aquests/", headers = [("Accept", "text/html")]),
        was.get ("@pypi/project/rs4/", headers = [("Accept", "text/html")])
    ]
    return was.futures (reqs).then (response)

@app.route ("/db")
def db (was):
    with was.db ("@sqlite3") as db:
        #db.execute('CREATE TABLE IF NOT EXISTS people (id real, name text)').commit ()
        #db.execute("INSERT INTO people (id, name) VALUES (2, 'Hans Roh')").commit ()
        req = db.execute ("select * from people")
    return was.API (data = req.fetch (cache = 40, timeout = 2))

@app.route ("/dbtx")
def dbtx (was):
    with was.transaction ("@sqlite3") as db:
        req = db.execute ("select * from people")
        return was.API (data = req.fetch ())

@app.route ("/dbmap")
def dbmap (was):
    with was.db.map ("@sqlite3m") as db:
        #db.execute('CREATE TABLE IF NOT EXISTS people (id real, name text)').commit ()
        #db.execute("INSERT INTO people VALUES (1, 'Hans Roh')").commit ()
        req = db.execute ("select * from people")
        results = req.dispatch ()
        data = req.fetch (cache = 60)
        assert data == results.data
    with was.db.map ("@sqlite3m") as db:
        db.execute ("delete from people where id=3").commit ()
    return was.API (data = data)

@app.route ("/dblb")
def dblb (was):
    with was.db.lb ("@sqlite3m") as db:
        req = db.execute ("select * from people")
    return was.API (req.fetch (cache = 40, timeout = 2))

@app.route ("/xmlrpc")
def xmlrpc (was):
    with was.xmlrpc ("@pypi/pypi") as stub:
        req = stub.package_releases ('roundup')
        assert req.fetch () == ['1.6.1']
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


if __name__ == "__main__":
    import skitai

    if os.name == "nt":
        skitai.set_service (ServiceConfig)

    skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
    skitai.alias ("@sqlite3", skitai.DB_SQLITE3, "resources/sqlite3.db")
    skitai.alias ("@sqlite3m", skitai.DB_SQLITE3, ["resources/sqlite3-1.db", "resources/sqlite3-2.db"])

    skitai.mount ("/", 'statics')
    skitai.mount ("/", app)
    skitai.mount ("/websocket", 'websocket.py')
    skitai.mount ("/rpc2", 'rpc2.py')
    skitai.mount ("/routeguide.RouteGuide", 'grpc_route_guide.py')
    skitai.mount ("/members", 'auth.py')
    skitai.mount ("/lb", "@pypi")
    skitai.enable_proxy ()

    skitai.run (
        port = 30371,
        workers = 1,
        threads = 4
    )

