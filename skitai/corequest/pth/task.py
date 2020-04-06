from concurrent.futures import TimeoutError, CancelledError
import time
from ..tasks import Mask
from .. import corequest
from skitai import was
from aquests.athreads import trigger
import sys
from ..httpbase.task import DEFAULT_TIMEOUT

class Task (corequest):
    def __init__ (self, future, name, meta):
        self.setup (name, meta)
        self.future = future

    def setup (self, name, meta, timeout = None):
        self._name = name
        self._meta = self.meta = meta
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

    def _settle (self, future):
        expt, result = future.exception (0), None
        if self._fulfilled:
            if not expt:
                result = future.result (0)
            mask = Mask (result, expt, meta = self._meta)
            self._late_respond (mask)

    def kill (self):
        try: self.future.result (timeout = 0)
        except: pass
        self.future.set_exception (TimeoutError)

    def cancel (self):
        try: self.future.cancel ()
        except: pass
        self.future.set_exception (CancelledError)

    def then (self, func):
        self._fulfilled = func
        self._was = self._get_was ()
        self.future.add_done_callback (self._settle)
        self._meta ['__reqid'] = 0
        return self

    # common corequest methods ----------------------------------
    def _create_mask (self, timeout):
        self._timeout = timeout
        if self._mask:
            return self._mask
        data = None
        expt = self.future.exception (timeout)
        if not expt:
            data = self.future.result (0)
        self._mask = Mask (data, expt, meta = self.meta)
        return self._mask

    def fetch (self, cache = None, cache_if = (200,), timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout).fetch ()

    def one (self, cache = None, cache_if = (200,), timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout).one ()

    def commit (self, timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout).commit ()

    def dispatch (self, timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout)
