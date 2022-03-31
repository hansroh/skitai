import threading
import asyncio
import queue
import time
from skitai.tasks.pth.task import Task

class CoroutineExecutor (threading.Thread):
    def __init__ (self, q):
        super ().__init__ ()
        self.q = q
        self.loop = asyncio.new_event_loop ()
        asyncio.set_event_loop (self.loop)
        threading.Thread (target = self.loop.run_forever).start ()

    def run (self):
        while 1:
            item = self.q.get ()
            if item is None:
                self.loop.call_soon_threadsafe (self.loop.stop)
                break
            coro, cb, pr = item
            future = asyncio.run_coroutine_threadsafe (coro, self.loop)
            wrap = Task (future, 'name', meta = {}, filter = None)
            pr = pr + (wrap,)
            cb (*pr)


def on_created (was, future):
    print (future, future.fetch ())

q = queue.Queue ()
t = CoroutineExecutor (q)
t.start ()
q.put ((asyncio.sleep (1.0, result = 5), on_created, ("was",)))
time.sleep (1.2)
q.put (None)


