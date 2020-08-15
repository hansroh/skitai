from atila import Atila
import time, math
import json
from services import route_guide_pb2
import os

app = Atila (__name__)
app.securekey = '0123456789'

@app.route ("/")
def index (was):
    return "CSRF: {}".format (was.csrf_token)

@app.route ("/post")
@app.csrf_verification_required
def post (was, **form):
    return 'OK'

@app.route ("/thread_future", methods = ['GET'])
def thread_future_respond (was):
    def thread_future_respond (was, tasks):
        time.sleep (0.03)
        return tasks.fetch ()
    return was.ThreadPass (thread_future_respond, args = (was.Mask ('Hello'),))

@app.route ('/map_in_thread')
def map_in_thread (was):
    def kk (was):
        return was.Map (media = was.Mask ('Hello'))
    return was.ThreadPass (kk)

@app.route ("/render_or_API")
def render_or_API (was):
    return was.render_or_API ("documentation.html", content = 'render')

@app.route ("/render_or_Map")
def render_or_Map (was):
    return was.render_or_Map ("documentation.html", content = was.Mask ('render'))

@app.route ("/render_or_Mapped")
def render_or_Mapped (was):
    tasks = was.Tasks (content = was.Mask ('render'))
    return was.render_or_Mapped ("documentation.html", tasks)

@app.route ("/reindeer")
def static (was):
    return was.MountedFile ('/img/reindeer.jpg')

@app.route ("/file")
def file (was):
    return was.File (os.path.join (os.path.dirname (__file__), 'statics/img/reindeer.jpg'))

@app.route ("/stream")
def stream (was):
    def stream ():
        for i in range (100):
            time.sleep (0.05)
            yield '<CHUNK>'
    return was.response ("210 Streaing", stream (), headers = [('Content-Type', 'text/plain')])

@app.route ("/stub")
def stub (was):
    with was.stub ("https://pypi.org", headers = [("Accept", "text/html")]) as stub:
        req1 = stub.get ("/project/rs4/")
    with was.stub ("https://pypi.org/project", headers = [("Accept", "text/html")]) as stub:
        req2 = stub.get ("/rs4/")
    with was.stub ("@pypi", headers = [("Accept", "text/html")]) as stub:
        req3 = stub.get ("/project/rs4/")
    with was.stub ("@pypi/project", headers = [("Accept", "text/html")]) as stub:
        req4 = stub.get ("/rs4/")
    req5 = was.get ("https://pypi.org/project/rs4/", headers = [("Accept", "text/html")])

    r = was.Tasks ([req1, req2, req3, req4, req5]).fetch ()
    return was.API (result = r)

def process_future_response (was, tasks):
    time.sleep (0.03)
    return 'test'


if __name__ == "__main__":
    import skitai
    skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
    skitai.mount ("/", app)
    skitai.mount ("/", 'statics')
    skitai.mount ("/lb", "@pypi")
    skitai.mount ("/lb2", "@pypi/project")
    skitai.run (port = 30371)
