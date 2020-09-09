import sys
from ..exceptions import HTTPError
from . import corequest, response
from .httpbase.task import DEFAULT_TIMEOUT, Task
from skitai import was
from rs4.attrdict import AttrDict
import time
from skitai import NORMAL
import warnings

class TaskBase (corequest):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, meta = None, keys = None):
        assert isinstance (reqs, (list, tuple))
        self._meta = self.meta = meta or {}
        if '__constants' not in self._meta and keys:
            self._meta ['__constants'] = {}
            idx = 0
            for key in keys [:]:
                if key is None:
                    break
                if not isinstance (reqs [idx], corequest):
                    self._meta ['__constants'][keys.pop (idx)] = reqs.pop (idx)
                else:
                    idx += 1

        self._reqs = reqs
        self._req_count = len (reqs)
        self._finished = False
        self._timeout = timeout
        self._keys = keys
        self._was = was

        if "__was_id" not in self._meta:
            for req in reqs:
                if req._meta:
                    self.meta ['__was_id'] = req._meta ['__was_id']
                    break
        self._init_time = time.time ()

    def set_callback (self, func, reqid = None, timeout = None):
        if reqid is not None:
            self._meta ["__reqid"] = reqid
        func (self)

    def _count (self):
        with self._was.cv:
            return 0 if self._finished else len (self._reqs)

    def set_cache (self, data, current_was):
        def find_key (data, keys):
            d = data
            for k in keys.split ('.'):
                d = d [k]
            return d

        max_age = self._meta.get ('maxage', 0)
        mtime = self._meta.get ('mtime')
        etag = self._meta.get ('etag')
        mtime and current_was.response.set_mtime (find_key (data, mtime), max_age = max_age)
        etag  and current_was.response.set_etag (find_key (data, etag), max_age = max_age)

    def dict (self, current_was = None):
        keys = self._keys
        if keys is None:
            raise AttributeError ('keys paramenter is not defined')

        results = self._reqs
        if self._req_count == 1 and not isinstance (results, (list, tuple)):
            results = [results]

        data = {}
        for idx, key in enumerate (keys):
            if key is None:
                results [idx].commit ()
                continue
            method, field = 'fetch', None
            option = key.split ('__')
            if len (option) >= 3:
                key, method, field = option
                if method not in  ('dict', 'fetch', 'one'):
                    raise RuntimeError ('method must be one of `one`, `fetch` or `dict` for specifying field')
                if method == 'fetch':
                    field = int (field)
            elif len (option) == 2:
                key, method = option
                if method not in ('one', 'fetch', 'dict'):
                    if method.isdigit ():
                        field, method = int (method), 'fetch'
                    else:
                        field, method = method, 'dict'

            result = results [idx]
            keydata = getattr (result, method) ()
            if field:
                keydata = keydata [field]
            data [key] = keydata

        current_was and self.set_cache (data, current_was)
        data.update (self._meta.get ('__constants', {}))
        return AttrDict (data)


class Tasks (TaskBase):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, meta = None, keys = None):
        TaskBase.__init__ (self, reqs, timeout, meta, keys)
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
            if hasattr (req, '_cv') and req._cv:
                # this is cached result
                req.reset_timeout (timeout, self._was.cv)
                _reqs.append (req)

        if not _reqs:
            return

        with self._was.cv:
            while sum ([req._count () for req in _reqs]) > 0:
                remain = timeout - (time.time () - self._init_time)
                if remain <= 0:
                    break
                self._was.cv.wait (remain)

        self._timeout = -1
        for req in _reqs:
            req.reset_timeout (-1, None)

        with self._was.cv:
            self._finished = True

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
        if self._keys and [_ for _ in self._keys if _]:
            return self.dict ()
        return [req.fetch (cache, cache_if, timeout) for req in self._reqs]

    def one (self, cache = None, cache_if = (200,), timeout = None):
        self._wait_for_all (timeout)
        return [req.one (cache, cache_if, timeout) for req in self._reqs]

    def cache (self, cache = 60, cache_if = (200,)):
        [r.cache (cache, cache_if) for r in self.results]

    def then (self, func, was = None):
        if not self._reqs:
            return func (self._was, self)
        return Futures (self._reqs, self._timeout, self.meta, self._keys).then (func, was)


class Mask (response, TaskBase):
    def __init__ (self, data = None, _expt = None, _status_code = None, meta = None, keys = None):
        self._expt = _expt
        self._data = data
        self._meta = self.meta = meta or {}
        self.status = NORMAL
        self.status_code = _status_code or (_expt and 500 or 200)
        self._timeout = DEFAULT_TIMEOUT
        self._keys = keys
        self._was = was

    def _reraise (self):
        if self._expt:
            raise self._expt

    def count (self):
        return 1

    def dispatch (self, cache = None, cache_if = (200,), timeout = None):
        return self

    def commit (self, *arg, **karg):
        self._reraise ()

    def fetch (self, *arg, **karg):
        self._reraise ()
        return self._data

    def one (self, *arg, **karg):
        self._reraise ()
        try:
            if len (self._data) == 0:
                raise HTTPError ("410 Partial Not Found")
            if len (self._data) != 1:
                raise HTTPError ("409 Conflict")
            return self._data [0]
        except TypeError:
            return self._data

    def then (self, func, was = None):
        return func (was or self._get_was (), self)


# completed future(s) ----------------------------------------------------
class CompletedTasks (response, Tasks):
    def __init__ (self, reqs, meta, keys):
        Tasks.__init__ (self, reqs, DEFAULT_TIMEOUT, meta, keys)
        self._finished = True

    def __del__ (self):
        self._reqs = [] #  reak back ref.

    def _wait_for_all (self, timeout):
        pass


class CompletedTask (CompletedTasks):
    def __iter__ (self):
        raise TypeError ('Future is not iterable')

    def __getitem__ (self, sliced):
        raise TypeError ('Future is not iterable')

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


class Revoke:
    # for ignoring return
    def __init__ (self):
        pass

# future(s) ----------------------------------------------------
class Futures (TaskBase, Revoke):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, meta = None, keys = None):
        if isinstance (reqs, Tasks):
            reqs = reqs._reqs
        TaskBase.__init__ (self, reqs, timeout, meta, keys)
        self._fulfilled = None
        self._responded = 0
        self._single = False

    def then (self, func, was = None):
        self._fulfilled = func
        self._was = was or self._get_was ()
        for reqid, req in enumerate (self._reqs):
            req.set_callback (self._collect, reqid, self._timeout)
        return self

    def _collect (self, res):
        self._responded += 1
        if self._responded == len (self._reqs):
            if self._fulfilled:
                tasks = (self._single and CompletedTask or CompletedTasks) (self._reqs, self.meta, self._keys)
                self._late_respond (tasks)
            else:
                self._was.response ("205 No Content", "")
                self._was.response.done ()


class Future (Futures):
    def __init__ (self, req, timeout = DEFAULT_TIMEOUT, meta = None, keys = None):
        Futures.__init__ (self, [req], timeout, meta, keys)
        self._single = True
