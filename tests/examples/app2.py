from atila import Atila
import time, math
import json
from services import route_guide_pb2
import os
import types
import threading

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


GENSQL = '''SELECT 'a', 1
   FROM (SELECT * FROM (
         (SELECT 0 UNION ALL SELECT 1) t2,
         (SELECT 0 UNION ALL SELECT 1) t4,
         (SELECT 0 UNION ALL SELECT 1) t8,
         (SELECT 0 UNION ALL SELECT 1) t16,
         (SELECT 0 UNION ALL SELECT 1) t32,
         (SELECT 0 UNION ALL SELECT 1) t64,
         (SELECT 0 UNION ALL SELECT 1) t128,
         (SELECT 0 UNION ALL SELECT 1) t256,
         (SELECT 0 UNION ALL SELECT 1) t512,
         (SELECT 0 UNION ALL SELECT 1) t1024,
         (SELECT 0 UNION ALL SELECT 1) t2048
         )
    )
'''
@app.route ("/threaproducer")
@app.inspect (ints = ['n', 'q'])
def threaproducer (was, n = 3, q = 3):
    def producer (cur):
        def produce (q):
            while 1:
                rows = cur.fetchmany (n)
                if not rows:
                    q.put (None)
                    break
                # print (len (rows))
                q.put (str (rows))
        return produce
    cur = was.cursor ("@sqlite3").execute (GENSQL)
    return was.Queue (producer (cur), q)

@app.route ("/stub")
def stub (was):
    with was.stub ("https://pypi.org", headers = [("Accept", "text/html")]) as stub:
        req1 = stub.get ("/{}/rs4/", 'project')
    with was.stub ("https://pypi.org/project", headers = [("Accept", "text/html")]) as stub:
        req2 = stub.get ("/rs4/")
    with was.stub ("@pypi", headers = [("Accept", "text/html")]) as stub:
        req3 = stub.get ("/project/rs4/")
    with was.stub ("@pypi/project", headers = [("Accept", "text/html")]) as stub:
        req4 = stub.get ("/{}/", 'rs4')
    req5 = was.get ("https://pypi.org/project/rs4/", headers = [("Accept", "text/html")])

    r = was.Tasks ([req1, req2, req3, req4, req5]).fetch ()
    return was.API (result = r)

@app.route ("/coroutine")
def coroutine (was):
    def respond (was, task):
        return task.fetch ()
    with was.stub ("http://example.com") as stub:
        return stub.get ("/").then (respond)

@app.route ("/coroutine/2")
@app.coroutine
def coroutine2 (was):
    with was.stub ("http://example.com") as stub:
        task = yield stub.get ("/")
    return task.fetch ()

@app.route ("/coroutine/3")
@app.coroutine
def coroutine3 (was):
    with was.stub ("http://example.com") as stub:
        task = yield stub.get ("/")
    with was.stub ("https://pypi.org/") as stub:
        task = yield stub.get ("/")
    return task.fetch ()

@app.route ("/coroutine/4")
@app.coroutine
def coroutine4 (was):
    with was.stub ("http://example.com") as stub:
        task1 = yield stub.get ("/")
    task2 = yield was.Mask ('mask')
    return was.API (a = task1.fetch (), b = task2.fetch ())

@app.route ("/coroutine/5")
@app.coroutine
def coroutine5 (was):
    with was.stub ("http://example.com") as stub:
        task1 = stub.get ("/")
    task2 = was.Mask ('mask')
    tasks = yield was.Tasks (task1, task2)
    a, b = tasks.fetch ()
    return was.API (a = a, b = b)

@app.route ("/coroutine/6", coroutine = True)
def coroutine6 (was):
    task1 = was.Mask ("Example Domain")
    task2 = was.Mask ('mask')
    tasks = yield was.Tasks (a = task1, b = task2)
    return was.API (**tasks.dict ())

@app.route ("/coroutine/7", coroutine = True)
def coroutine7 (was):
    task1 = was.Mask ("Example Domain")
    task2 = was.Mask ('mask')
    tasks = yield was.Tasks (a = task1, b = task2)
    return was.API (**tasks.fetch ())

@app.route ("/coroutine/8", coroutine = True)
def coroutine8 (was):
    task1 = was.Mask ("Example Domain")
    task2 = was.Mask ('mask')
    tasks = yield was.Tasks (a = task1, b = task2)
    return was.Map (c = was.Mask (100), **tasks.fetch ())

def wait_hello (timeout = 1.0):
    time.sleep (timeout)
    return 'mask'

@app.route ("/coroutine/9", coroutine = True)
def coroutine9 (was):
    task1 = was.Mask ("Example Domain")
    task2 = was.Thread (wait_hello, args = (1.0,))
    tasks = yield was.Tasks (a = task1, b = task2)
    task3 = yield was.Thread (wait_hello, args = (1.0,))
    task4 = yield was.Subprocess ('ls')
    return was.API (d = task4.fetch (), c = task3.fetch (), **tasks.fetch ())

@app.route ("/coroutine/10", coroutine = True)
def coroutine10 (was):
    task1 = was.Mask ("Example Domain")
    task2 = was.Thread (wait_hello, args = (1.0,))
    tasks = yield was.Tasks (a = task1, b = task2)
    task3 = yield was.Process (wait_hello, args = (1.0,))
    task4 = yield was.Subprocess ('ls')
    return was.Map (d = task4, c__fetch = task3, **tasks.fetch ())

@app.route ("/coroutine/11", coroutine = True)
def coroutine11 (was):
    task1 = was.Mask ("Example Domain")
    task2 = was.Mask ('mask')
    if 0:
        yield was.Tasks (a = task1, b = task2)
    return was.Map (c = was.Mask (100), a = task1, b = task2)

@app.route ("/coroutine_generator", coroutine = True)
@app.inspect (ints = ['n', 'h', 'f'])
def coroutine_generator (was, n = 1, h = 0, f = 0):
    if h:
        yield "Header Line\n"
    for i in range (n):
        task = yield (was.Mask ("Example Domain"))
        yield task.fetch ()
        if f:
            yield '\n'

@app.route ("/coroutine_streaming", methods = ['POST'], coroutine = True, input_stream = True)
def coroutine_streaming (was):
    while 1:
        data = yield was.Input (16184)
        #print ('chunk', len (data))
        if not data:
            break
        yield b':' + data

@app.route ("/coroutine_streaming2", methods = ['POST'], coroutine = True, input_stream = True)
def coroutine_streaming2 (was):
    while 1:
        data = yield was.Input (16184)
        print ('chunk', len (data))
        if not data:
            break
        yield b':' + data

def process_future_response (was, tasks):
    time.sleep (0.03)
    return 'test'


if __name__ == "__main__":
    import skitai
    skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
    skitai.alias ("@sqlite3", skitai.DB_SQLITE3, "resources/sqlite3.db")
    skitai.mount ("/", app)
    skitai.mount ("/", 'statics')
    skitai.mount ("/lb", "@pypi")
    skitai.mount ("/lb2", "@pypi/project")
    skitai.run (port = 30371)
