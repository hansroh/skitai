import multiprocessing
import rs4
from rs4.logger import screen_logger
import time
import sys
from concurrent.futures import TimeoutError
import threading
import asyncio
from collections import deque
from . import utils
from .pth.task import Task

class ProcessExpired (Exception):
    pass

DEFAULT_TIMEOUT = 10
N_CPU = multiprocessing.cpu_count()

class ThreadExecutor:
    NAME = "thread"
    MAINTERN_INTERVAL = 10

    def __init__ (self, workers = None, default_timeout = None, logger = None):
        self.logger = logger
        self.workers = workers or N_CPU
        self.default_timeout = default_timeout
        self.last_maintern = time.time ()
        self.lock = multiprocessing.Lock ()
        self.executor = None
        self.futures = []
        self.no_more_request = False

        self._dones = 0
        self._timeouts = 0
        self._expires = 0
        self._exceptions = 0

    def __len__ (self):
        with self.lock:
            return len (self.futures)

    def launch_executor (self):
        self.executor = rs4.tpool (self.workers)

    def status (self):
        with self.lock:
            return dict (
                completions = self._dones,
                timeouts = self._timeouts,
                expires = self._expires,
                exceptions = self._exceptions,
                maintainables = len (self.futures),
                default_timeout = self.default_timeout,
                workers = self.workers,
                last_maintern = self.last_maintern,
                activated = self.executor is not None,
                tasks = [f.get_name () for f in self.futures if not f.done ()]
            )

    def maintern (self, now):
        self.last_maintern = now
        inprogresses = []
        for future in self.futures:
            if future.dispatched ():
                continue

            if future.done ():
                self._dones += 1
                try:
                    future.result ()
                except TimeoutError as error:
                    self.logger ("{} task took longer than {} seconds: {}".format (self.NAME, error.args[1], future), 'error')
                    self._timeouts += 1
                except ProcessExpired as error:
                    self.logger ("{} task died unexpectedly with exit code {}: {}".format (self.NAME, error.exitcode, future), 'error')
                    self._expires += 1
                except Exception as error:
                    self.logger.trace ()
                    self._exceptions += 1
                continue

            inprogresses.append (future)
        self.futures = inprogresses

    def shutdown (self):
        with self.lock:
            self.no_more_request = True
            if not self.executor:
                return
            self.maintern (time.time ())
            if sys.version_info [:2] >= (3, 9):
                self.executor.shutdown (cancel_futures = True)
            else:
                self.executor.shutdown ()
            self.executor = None
            self.futures = []

            return len (self.futures)

    def create_task (self, f, a, b, timeout):
        return self.executor.submit (f, *a, **b)

    def __call__ (self, was_id, f, *a, **b):
        with self.lock:
            if self.no_more_request:
                return
            if self.executor is None:
                self.launch_executor ()
            else:
                now = time.time ()
                if now > self.last_maintern + self.MAINTERN_INTERVAL:
                    self.maintern (now)

        meta = {}
        timeout, filter = None, None
        if b:
            try:
                timeout = b.pop ('timeout')
            except KeyError:
                timeout = self.default_timeout
            try: meta = b.pop ('meta')
            except KeyError: pass
            try: filter = b.pop ('filter')
            except KeyError: pass
            try: a = b.pop ('args')
            except KeyError: pass
            b = b.get ('kwargs', b)

        meta ['__was_id'] = was_id
        future = self.create_task (f, a, b, timeout)
        wrap = Task (future, "{}.{}".format (f.__module__, f.__name__), meta = meta, filter = filter)
        timeout and wrap.set_timeout (timeout)
        # self.logger ("{} task started: {}".format (self.NAME, wrap))
        with self.lock:
            self.futures.append (wrap)
        return wrap

class ProcessExecutor (ThreadExecutor):
    NAME = "process"
    def launch_executor (self):
        self.executor = rs4.ppool (self.workers)

    def create_task (self, f, a, b, timeout = None):
        return self.executor.submit (f, *a, **b)


# ------------------------------------------------------------------------

class Executors:
    def __init__ (self, workers = N_CPU, default_timeout = DEFAULT_TIMEOUT, logger = None):
        self.logger = logger or screen_logger ()
        self.executors = [
            ThreadExecutor (workers, default_timeout, self.logger),
            ProcessExecutor (workers, default_timeout, self.logger)
        ]

    def status (self):
        return dict (
            thread = self.executors [0].status (),
            process = self.executors [1].status ()
        )

    def cleanup (self):
        return [e.shutdown () for e in self.executors]

    def create_thread (self, was_id, f, *a, **b):
        return self.executors [0] (was_id, f, *a, **b)

    def create_process (self, was_id, f, *a, **b):
        return self.executors [1] (was_id, f, *a, **b)

    def _get_pool (self, executor):
        if executor.executor is None:
            executor.launch_executor ()
        return executor.executor

    def get_tpool (self):
        return self._get_pool (self.executors [0])

    def get_ppool (self):
        return self._get_pool (self.executors [1])


class AsyncExecutor (threading.Thread):
    def __init__ (self, max_task = 10):
        super ().__init__ ()
        try:
            import uvloop
        except ImportError:
            pass
        else:
            asyncio.set_event_loop_policy (uvloop.EventLoopPolicy ())
        self.loop = asyncio.new_event_loop ()
        asyncio.set_event_loop (self.loop)
        self.max_task = max_task
        self.queue = deque ()
        self.lock = threading.Condition ()
        self.cv = threading.Condition ()
        self.futures = {}
        self.current_tasks = 0
        threading.Thread (target = self.start_event_loop).start ()

    def start_event_loop (self):
        asyncio.set_event_loop (self.loop)
        self.loop.run_forever ()

    def run (self):
        while 1:
            with self.lock:
                while len (self.queue) == 0 or self.current_tasks > self.max_task:
                    self.lock.wait ()
                item = self.queue.popleft ()

            if item is None:
                self.loop.call_soon_threadsafe (self.loop.stop)
                break

            tid, was, task_class, coro, callback = item
            meta  = {'__was_id': was.ID, 'coro': coro}
            future = asyncio.run_coroutine_threadsafe (coro, self.loop)
            task = [ task_class (future, coro.__qualname__, meta = meta, filter = None).then (callback, was) ]

            with self.lock:
                self.current_tasks += 1

            with self.cv:
                self.futures [tid] = task
                self.cv.notify ()

    def get (self, tid):
        with self.cv:
            while tid not in self.futures:
                self.cv.wait ()
            return self.futures.pop (tid)

    def put (self, item):
        tid = None
        if item:
            was, coro, response_callback, after_request_callback = item
            _was = utils.get_cloned_context (was.ID)
            _was.request.postprocessing = after_request_callback
            utils.deceive_context (_was, coro)
            tid = _was.txnid ()
            item = (tid, _was, Task, coro, response_callback)

        with self.lock:
            self.queue.append (item)
            self.lock.notify ()

        return self.get (tid) if tid else None

    def done (self):
        with self.lock:
            self.current_tasks -= 1
            self.lock.notify ()

    def cleanup (self):
        self.put (None)
