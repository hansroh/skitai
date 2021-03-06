import sys
from ..exceptions import HTTPError
from . import corequest, response
from .httpbase.task import DEFAULT_TIMEOUT, Task
from skitai import was
from rs4.attrdict import AttrDict
import time
from skitai import NORMAL

class TaskBase (corequest):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, **meta):
        assert isinstance (reqs, (list, tuple))
        self._timeout = timeout
        self._reqs = reqs
        self.meta = meta
        self._init_time = time.time ()

    def __getattr__ (self, name):
        try:
            return self.meta [name]
        except KeyError:
            raise AttributeError ("{} cannot found".format (name))

class Tasks (TaskBase):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, **meta):
        TaskBase.__init__ (self, reqs, timeout, **meta)
        self._results = []

    def __iter__ (self):
        return iter (self._reqs)

    def __getitem__ (self, sliced):
        return self._reqs [sliced].dispatch ()

    def set_timeout (self, timeout):
        self._timeout = timeout

    def add (self, req):
        self._reqs.append (req)

    def merge (self, tasks):
        for req in tasks._reqs:
            self.add (req)

    def _wait_for_all (self, timeout):
        timeout = timeout or self._timeout
        _reqs = []
        for req in self._reqs:
            if hasattr (req, '_cv'):
                req.reset_timeout (timeout, was.cv)
                _reqs.append (req)

        if not _reqs:
            return

        with was.cv:
            while sum ([req._count () for req in _reqs]) > 0:
                remain = timeout - (time.time () - self._init_time)
                if remain <= 0:
                    break
                was.cv.wait (remain)

        self._timeout = -1
        for req in _reqs:
            req.reset_timeout (-1, None)

    #------------------------------------------------------
    def dispatch (self, cache = None, cache_if = (200,), timeout = None):
        self._wait_for_all (timeout)
        return [req.dispatch (cache, cache_if) for req in self._reqs]

    def wait (self, timeout = None):
        self._wait_for_all (timeout)
        return [req.wait (timeout) for req in self._reqs]

    def commit (self, timeout = None):
        self._wait_for_all (timeout)
        [req.commit (timeout) for req in self._reqs]

    def fetch (self, cache = None, cache_if = (200,), timeout = None):
        self._wait_for_all (timeout)
        return [req.fetch (cache, cache_if, timeout) for req in self._reqs]

    def one (self, cache = None, cache_if = (200,), timeout = None):
        self._wait_for_all (timeout)
        return [req.one (cache, cache_if, timeout) for req in self._reqs]

    def cache (self, cache = 60, cache_if = (200,)):
        [r.cache (cache, cache_if) for r in self.results]

    def then (self, func):
        return Futures (self._reqs, self._timeout, **self.meta).then (func)


class Mask (response, TaskBase):
    def __init__ (self, data = None, _expt = None, _status_code = None, **meta):
        self._expt = _expt
        self._data = data
        self.meta = meta
        self.status = NORMAL
        self.status_code = _status_code or (_expt and 500 or 200)
        self._timeout = DEFAULT_TIMEOUT

    def _reraise (self):
        if self._expt:
            raise self._expt

    def dispatch (self, cache = None, cache_if = (200,), timeout = None):
        return self

    def commit (self, *arg, **karg):
        self._reraise ()

    def fetch (self, *arg, **karg):
        self._reraise ()
        return self._data

    def one (self, *arg, **karg):
        self._reraise ()
        if len (self._data) == 0:
            raise HTTPError ("410 Partial Not Found")
        if len (self._data) != 1:
            raise HTTPError ("409 Conflict")
        return self._data [0]

# completed future(s) ----------------------------------------------------
class CompletedTasks (response, Tasks):
    def __init__ (self, reqs, **meta):
        Tasks.__init__ (self, reqs, **meta)

    def __del__ (self):
        self._reqs = [] #  reak back ref.

class CompletedTask (CompletedTasks):
    def __iter__ (self):
        raise TypeError ('Futrue is not iterable')

    def __getitem__ (self, sliced):
        raise TypeError ('Futrue is not iterable')

    #------------------------------------------------------
    def dispatch (self, cache = None, cache_if = (200,), timeout = None):
        rss = CompletedTasks.dispatch (self, cache, cache_if, timeout)
        return rss [0]

    def fetch (self, cache = None, cache_if = (200,), timeout = None):
        rss = CompletedTasks.fetch (self, cache, cache_if, timeout)
        return rss [0]

    def one (self, cache = None, cache_if = (200,), timeout = None):
        rss = CompletedTasks.one (self, cache, cache_if, timeout)
        return rss [0]

    def wait (self, timeout = None):
        rss = CompletedTasks.wait (self, timeout)
        return rss [0]

    def commit (self, timeout = None):
        rss = CompletedTasks.commit (self, timeout)
        return rss [0]

# future(s) ----------------------------------------------------
class Futures (TaskBase):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, **meta):
        if isinstance (reqs, Tasks):
            reqs = reqs._reqs
        TaskBase.__init__ (self, reqs, timeout, **meta)
        self._was = None
        self._fulfilled = None
        self._responded = 0
        self._single = False

    def then (self, func):
        self._fulfilled = func
        self._was = self._get_was ()
        for reqid, req in enumerate (self._reqs):
           req.set_callback (self._collect, reqid, self._timeout)
        return self

    def _collect (self, res):
        self._responded += 1
        if self._responded == len (self._reqs):
            if self._fulfilled:
                tasks = (self._single and CompletedTask or CompletedTasks) (self._reqs, **self.meta)
                self._late_respond (tasks)
            else:
                self._was.response ("205 No Content", "")
                self._was.response.done ()


class Future (Futures):
    def __init__ (self, req, timeout, **meta):
        Futures.__init__ (self, [req], timeout, **meta)
        self._single = True

