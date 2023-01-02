from atila import Atila
import time, math
import json
try:
    from services import route_guide_pb2
except ImportError:
    from services import route_guide_pb2_v3 as route_guide_pb2
import os
import types
import threading

app = Atila (__name__)
app.securekey = '0123456789'

@app.route ("/")
def index (context):
    return "CSRF: {}".format (context.csrf_token)

@app.route ("/post")
@app.csrf_verification_required
def post (context, **form):
    return 'OK'

@app.route ("/thread_future", methods = ['GET'])
def thread_future_respond (context):
    def thread_future_respond (context, tasks):
        time.sleep (0.03)
        return tasks.fetch ()
    return context.ThreadPass (thread_future_respond, args = (context.Mask ('Hello'),))

@app.route ('/map_in_thread')
def map_in_thread (context):
    def kk (context):
        return context.Map (media = context.Mask ('Hello'))
    return context.ThreadPass (kk)

@app.route ("/render_or_API")
def render_or_API (context):
    return context.render_or_API ("documentation.html", content = 'render')

@app.route ("/render_or_Map")
def render_or_Map (context):
    return context.render_or_Map ("documentation.html", content = context.Mask ('render'))

@app.route ("/render_or_Mapped")
def render_or_Mapped (context):
    tasks = context.Tasks (content = context.Mask ('render'))
    return context.render_or_Mapped ("documentation.html", tasks)

@app.route ("/reindeer")
def static (context):
    return context.MountedFile ('/img/reindeer.jpg')

@app.route ("/file")
def file (context):
    return context.File ('statics/img/reindeer.jpg')

@app.route ("/stream")
def stream (context):
    def stream ():
        for i in range (100):
            time.sleep (0.05)
            yield '<CHUNK>'
    return context.response ("210 Streaing", stream (), headers = [('Content-Type', 'text/plain')])

@app.route ("/threaproducer")
@app.spec (ints = ['n', 'max_size'])
def threaproducer (context, n = 3, max_size = 3):
    def produce (queue):
        cur = [('a', 1)] * 10000
        while 1:
            rows, cur = cur [:n], cur [n:]
            if not rows:
                queue.put (None)
                break
            # print (len (rows))
            queue.put (str (rows))
    return context.Queue (produce, max_size)

@app.route ("/stub")
def stub (context):
    req1 = context.Mask ("pypi/skitai/hansroh/rs4")
    req2 = context.Mask ("pypi/skitai/hansroh/rs4")
    req3 = context.Mask ("pypi/skitai/hansroh/rs4")
    req4 = context.Mask ("pypi/skitai/hansroh/rs4")
    req5 = context.Mask ("pypi/skitai/hansroh/rs4")

    r = context.Tasks ([req1, req2, req3, req4, req5]).fetch ()
    return context.API (result = r)

def fake ():
    time.sleep (1)
    return "pypi/skitai/hansroh/rs4"

def mask ():
    time.sleep (1)
    return "mask"

def process_future_response (context, tasks):
    time.sleep (0.03)
    return 'test'


if __name__ == "__main__":
    import skitai
    skitai.mount ("/", app)
    skitai.mount ("/", 'statics')
    skitai.run (port = 30371)
