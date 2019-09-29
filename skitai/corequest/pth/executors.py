import multiprocessing
import rs4
from rs4.logger import screen_logger
import time
from .task import Task

N_CPU = multiprocessing.cpu_count()

class ThreadExecutor:
    NAME = "thread"
    MAINTERN_INTERVAL = 30

    def __init__ (self, workers = None, zombie_timeout = None, logger = None):
        self.logger = logger
        self.workers = workers or N_CPU
        self.zombie_timeout = zombie_timeout
        self.last_maintern = time.time ()
        self.lock = multiprocessing.Lock ()
        self.executor = None
        self.futures = []
        self.no_more_request = False

        self._dones = 0
        self._timeouts = 0

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
                maintainables = len (self.futures),
                zombie_timeout = self.zombie_timeout,
                workers = self.workers,
                last_maintern = self.last_maintern,
                activated = self.executor is not None,
                tasks = [f.get_name () for f in self.futures if not f.done ()]
            )

    def maintern (self, now):
        self.last_maintern = now
        inprogresses = []
        for future in self.futures:
            if future.done ():
                self._dones += 1
                continue

            if self.no_more_request:
                timeout = -1 # kill immediately
            else:
                timeout = future.get_timeout ()
                if timeout is None:
                    timeout = self.zombie_timeout

            # timeout is 0 or None, it is infinite task
            if timeout is not None and future._started + timeout < now:
                future.kill ()
                self._timeouts += 1
                self.logger ("zombie {} task is killed: {}".format (self.NAME, future))
            else:
                inprogresses.append (future)
                continue
        self.futures = inprogresses

    def shutdown (self):
        with self.lock:
            self.no_more_request = True
            if not self.executor:
                return
            self.maintern (time.time ())
            self.executor.shutdown (wait = False)
            self.executor = None
            self.futures = []
            return len (self.futures)

    def __call__ (self, f, *a, **b):
        with self.lock:
            if self.no_more_request:
                return
            if self.executor is None:
                self.launch_executor ()
            else:
                now = time.time ()
                if now > self.last_maintern + self.MAINTERN_INTERVAL:
                    self.maintern (now)

        try:
            timeout = b.pop ('__timeout')
        except KeyError:
            timeout = None

        future = self.executor.submit (f, *a, **b)
        wrap = Task (future, "{}.{}".format (f.__module__, f.__name__))
        timeout and wrap.set_timeout (timeout)
        self.logger ("{} task started: {}".format (self.NAME, wrap))
        with self.lock:
            self.futures.append (wrap)
        return wrap

class ProcessExecutor (ThreadExecutor):
    NAME = "process"
    def launch_executor (self):
        self.executor = rs4.ppool (self.workers)


# ------------------------------------------------------------------------

class Executors:
    def __init__ (self, workers = N_CPU, zombie_timeout = None, logger = None):
        self.logger = logger or screen_logger ()
        self.executors = [
            ThreadExecutor (workers, zombie_timeout, self.logger),
            ProcessExecutor (workers, zombie_timeout, self.logger)
        ]

    def status (self):
        return dict (
            thread = self.executors [0].status (),
            process = self.executors [1].status ()
        )

    def cleanup (self):
        return [e.shutdown () for e in self.executors]

    def create_thread (self, f, *a, **b):
        return self.executors [0] (f, *a, **b)

    def create_process (self, f, *a, **b):
        return self.executors [1] (f, *a, **b)

