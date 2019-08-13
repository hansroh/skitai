from concurrent.futures import TimeoutError, CancelledError
import time
from ..tasks import Mask
from .. import corequest
from skitai import was
from aquests.athreads import trigger
import sys
from ..httpbase.task import DEFAULT_TIMEOUT

class Task (corequest):
    def __init__ (self, future, name):
        self.future = future
        self._name = name
        self._started = time.time ()
        self._was = None
        self._fulfilled = None
        self._mask = None

    def __str__ (self):
        return self._name

    def __getattr__ (self, name):
        return getattr (self.future, name)

    def _settle (self, future):
        expt, result = future.exception (0), None
        if self._fulfilled:
            if not expt:
                result = future.result (0)
            task = Mask (result, expt)            
            try:
                self._fulfilled (self._was, task)
            except:
                self._was.traceback ()        
                trigger.wakeup (lambda p = self._was.response, d = self._was.app.debug and sys.exc_info () or None: (p.error (500, "Internal Server Error", d), p.done ()) )
            else:
                trigger.wakeup (lambda p = self._was.response: (p.done (),))
            self._fulfilled = None
    
    def kill (self):
        try: self.future.result (timeout = 0)
        except: pass
        self.future.set_exception (TimeoutError)            

    def cancel (self):
        try: self.future.cancel ()
        except: pass
        self.future.set_exception (CancelledError) 

    def returning (self, returning):
        return returning

    def then (self, func):
        self._fulfilled = func
        try: self._was = was._clone (True)
        except TypeError: pass
        self.future.add_done_callback (self._settle)
        return self
    
    # common corequest methods ----------------------------------    
    def _create_mask (self, timeout):
        if self._mask:
            return self._mask
        data = None
        expt = self.future.exception (timeout)
        if not expt:
            data = self.future.result (0)
        self._mask = Mask (data, expt)
        return self._mask
    
    def fetch (self, cache = None, cache_if = (200,), timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout).fetch ()
        
    def one (self, cache = None, cache_if = (200,), timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout).one ()
        
    def commit (self, timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout).commit ()
    
    def dispatch (self, timeout = DEFAULT_TIMEOUT):
        return self._create_mask (timeout)    