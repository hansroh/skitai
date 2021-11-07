import time
import threading

DEFAULT_ZOMBIE_TIMEOUT = 60
DEFAULT_KEEP_ALIVE = 2

class ConnectProxy:
    def __init__ (self, asyncon):
        self._asyncon = asyncon
        self._args = None
        self._timeout = 30
        self._cv = threading.Condition ()

    def __getattr__ (self, attr):
        return getattr (self._asyncon, attr)

    def set_timeout (self, timeout):
        self._timeout = timeout

    def set_active (self, flag):
        if flag:
            return
        # exception occured
        self._args = None

    def _canceled (self):
        # must be called from very first line of execute_late
        if self._args is None:
            self._asyncon.set_active (False)
            return True
        return False

    def execute (self, *args):
        self._args = args
        self._asyncon.add_task (self.execute_late)

    def execute_late (self):
        if self._canceled ():
            return
        raise NotImplementedError


class BaseConnect:
    def __init__ (self, lock, logger):
        self.lock = lock
        self.logger = logger

        self.active = 0
        self.request_count = 0
        self.event_time = 0
        self.backend = False
        self.zombie_timeout = DEFAULT_ZOMBIE_TIMEOUT
        self.keep_alive = DEFAULT_KEEP_ALIVE

        self._history = []
        self._tasks = []
        self._no_more_request = False
        self._cv = threading.Condition ()

    def get_history (self):
        return self._history

    def log_history (self, msg):
        self._history.append (msg)

    def set_backend (self, backend_keep_alive = 10):
        self.backend = True
        self.keep_alive = backend_keep_alive

    def get_request_count (self):
        return self.request_count

    def set_timeout (self, timeout = 10):
        # CAUTION: used at proxy.tunnel_handler
        self.zombie_timeout = timeout

    def set_event_time (self):
        self.event_time = time.time ()

    def _set_active (self, flag):
        if flag:
            flag = time.time ()
            self.request_count += 1
        else:
            flag = 0
            self.set_timeout (self.keep_alive)
            if self._tasks:
                self._set_active (True)
                return self._tasks.pop (0)
        self.active = flag

    def set_active (self, flag, nolock = False):
        if nolock or self.lock is None:
            task = self._set_active (flag)
        else:
            with self.lock:
                task = self._set_active (flag)
        task and task ()

    def _add_task (self, task):
        if self.active > 0:
            self._tasks.append (task)
            return
        self._set_active (True)
        return task

    def add_task (self, task):
        if self.lock is None:
            task = self._add_task (task)
        else:
            with self.lock:
                task = self._add_task (task)
        task and task ()

    def get_active (self, nolock = False):
        if nolock or self.lock is None:
            return self.active
        with self.lock:
            return self.active

    def isactive (self):
        return self.get_active () > 0
