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

@app.route ("/coroutine")
def coroutine (context):
    def respond (context, task):
        return task.fetch ()
    return context.Mask ("pypi/skitai/hansroh/rs4").then (respond)

def fake ():
    time.sleep (1)
    return "pypi/skitai/hansroh/rs4"

def mask ():
    time.sleep (1)
    return "mask"

@app.route ("/coroutine/2")
@app.coroutine
def coroutine2 (context):
    task = yield context.Thread (fake)
    return task.fetch ()

@app.route ("/coroutine/3")
@app.coroutine
def coroutine3 (context):
    task = yield context.Thread (fake)
    task.fetch ()
    task = yield context.Thread (fake)
    return task.fetch ()

@app.route ("/coroutine/4")
@app.coroutine
def coroutine4 (context):
    task1 = yield context.Thread (fake)
    task2 = yield context.Thread (mask)
    return context.API (a = task1.fetch (), b = task2.fetch ())

@app.route ("/coroutine/5")
@app.coroutine
def coroutine5 (context):
    task1 = context.Mask ("pypi/skitai/hansroh/rs4")
    task2 = context.Mask ('mask')
    tasks = yield context.Tasks (task1, task2)
    a, b = tasks.fetch ()
    return context.API (a = a, b = b)

@app.route ("/coroutine/6", coroutine = True)
def coroutine6 (context):
    task1 = context.Mask ("pypi/skitai/hansroh/rs4")
    task2 = context.Mask ('mask')
    tasks = yield context.Tasks (a = task1, b = task2)
    return context.API (**tasks.dict ())

@app.route ("/coroutine/7", coroutine = True)
def coroutine7 (context):
    task1 = context.Mask ("pypi/skitai/hansroh/rs4")
    task2 = context.Mask ('mask')
    tasks = yield context.Tasks (a = task1, b = task2)
    return context.API (**tasks.fetch ())

@app.route ("/coroutine/8", coroutine = True)
def coroutine8 (context):
    task1 = context.Mask ("pypi/skitai/hansroh/rs4")
    task2 = context.Mask ('mask')
    tasks = yield context.Tasks (a = task1, b = task2)
    return context.Map (c = context.Mask (100), **tasks.fetch ())

def wait_hello (timeout = 1.0):
    time.sleep (timeout)
    return 'mask'

@app.route ("/coroutine/9", coroutine = True)
def coroutine9 (context):
    task1 = context.Thread (fake)
    task2 = context.Thread (wait_hello, args = (1.0,))
    tasks = yield context.Tasks (a = task1, b = task2)
    task3 = yield context.Thread (wait_hello, args = (1.0,))
    task4 = yield context.Subprocess ('ls')
    return context.API (d = task4.fetch (), c = task3.fetch (), **tasks.fetch ())

@app.route ("/coroutine/10", coroutine = True)
def coroutine10 (context):
    task1 = context.Mask ("pypi/skitai/hansroh/rs4")
    task2 = context.Thread (wait_hello, args = (1.0,))
    tasks = yield context.Tasks (a = task1, b = task2)
    task3 = yield context.Process (wait_hello, args = (1.0,))
    task4 = yield context.Subprocess ('ls')
    return context.Map (d = task4, c__fetch = task3, **tasks.fetch ())

@app.route ("/coroutine/11", coroutine = True)
def coroutine11 (context):
    task1 = context.Mask ("pypi/skitai/hansroh/rs4")
    task2 = context.Mask ('mask')
    if 0:
        yield context.Tasks (a = task1, b = task2)
    return context.Map (c = context.Mask (100), a = task1, b = task2)

@app.route ("/coroutine_generator", coroutine = True)
@app.spec (ints = ['n', 'h', 'f'])
def coroutine_generator (context, n = 1, h = 0, f = 0):
    if h:
        yield "Header Line\n"
    for i in range (n):
        task = yield (context.Mask ("pypi/skitai/hansroh/rs4"))
        yield task.fetch ()
        if f:
            yield '\n'

@app.route ("/coroutine_streaming", methods = ['POST'], coroutine = True, input_stream = True)
def coroutine_streaming (context):
    while 1:
        data = yield context.Input (16184)
        #print ('chunk', len (data))
        if not data:
            break
        yield b':' + data

@app.route ("/coroutine_streaming2", methods = ['POST'], coroutine = True, input_stream = True)
def coroutine_streaming2 (context):
    while 1:
        data = yield context.Input (16184)
        print ('chunk', len (data))
        if not data:
            break
        yield b':' + data

def process_future_response (context, tasks):
    time.sleep (0.03)
    return 'test'


if __name__ == "__main__":
    import skitai
    skitai.mount ("/", app)
    skitai.mount ("/", 'statics')
    skitai.run (port = 30371)
