import threading
import asyncio
from .task import Task

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
            coro, callback = item
            future = asyncio.run_coroutine_threadsafe (coro, self.loop)
            wrap = Task (future, 'name', meta = {}, filter = None)
            callback (wrap)

    def cleanup (self):
        self.q.put (None)
