import time
from ..derivations import Mask
from .. import Revoke
from .. import Task
from .. import DEFAULT_TIMEOUT

class Task (Task, Revoke):
    def __init__ (self, future, name, meta, filter, timeout = None):
        self.setup (name, meta, filter, timeout)
        self.future = future

    def setup (self, name, meta, filter, timeout):
        self._name = name
        self._meta = self.meta = meta or {}
        self._filter = filter
        self._started = time.time ()
        self._was = None
        self._fulfilled = None
        self._mask = None
        self._timeout = timeout

    def __str__ (self):
        return self._name

    def __getattr__ (self, name):
        return getattr (self.future, name)

    def get_name (self):
        return self._name

    def _settle (self, future = None):
        if self._fulfilled:
            mask = self._create_mask (0)
            if '__reqid' in self._meta:
                self._fulfilled (mask)
                self._fulfilled = None
            else:
                self._late_respond (self._mask)

    def dispatched (self):
        return self._mask is not None

    def result (self, timeout = None):
        expt = self.future.exception ()
        if expt:
            raise expt
        return self.future.result ()

    def kill (self):
        self.cancel ()

    def cancel (self):
        try: self.future.cancel ()
        except: pass
        # self.future.set_exception (CancelledError)

    def set_callback (self, func, reqid = None, timeout = None):
        if reqid is not None:
            self._meta ["__reqid"] = reqid
        self._timeout = timeout
        self._fulfilled = func
        self.future.add_done_callback (self._settle)

    def then (self, func = None, was = None):
        self._fulfilled = func or "self"
        self._was = was or self._get_was ()
        self.future.add_done_callback (self._settle)
        return self

    # common Task methods ----------------------------------
    def _create_mask (self, timeout):
        self._timeout = timeout
        if self._mask:
            return self._mask

        expt, data = None, None
        try:
            data = self.future.result ()
        except Exception as error:
            expt = error

        if not expt:
            if self._filter:
                data =  self._filter (data)

        self._mask = Mask (data, expt, meta = self.meta)
        return self._mask

    def fetch (self, cache = None, cache_if = (200,), timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout).fetch ()

    def one (self, cache = None, cache_if = (200,), timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout).one ()

    def commit (self, cache = None, cache_if = (200,), timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout).commit ()

    def dispatch (self, cache = None, cache_if = (200,), timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout)
