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

@app.route ("/render_or_API")
def render_or_API (was):
    return was.render_or_API ("documentation.html", content = 'render')

@app.route ("/render_or_Map")
def render_or_Map (was):
    return was.render_or_Map ("documentation.html", content = was.Mask ('render'))

@app.route ("/reindeer")
def static (was):
    return was.Static ('/img/reindeer.jpg')

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

def process_future_response (was, tasks):
    time.sleep (0.03)
    return 'test'

@app.route ("/thread_future", methods = ['GET'])
def thread_future_respond (was):
    def thread_future_respond (was, tasks):
        time.sleep (0.03)
        return tasks.fetch ()
    return was.ThreadFuture (thread_future_respond, args = (was.Mask ('Hello'),))


if __name__ == "__main__":
	import skitai
	skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
	skitai.mount ("/", app)
	skitai.mount ("/", 'statics')
	skitai.mount ("/lb", "@pypi")
	skitai.mount ("/lb2", "@pypi/project")
	skitai.run (port = 30371)
