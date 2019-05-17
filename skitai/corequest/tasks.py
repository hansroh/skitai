import sys
from ..utility import make_pushables
from ..exceptions import HTTPError
from . import corequest, response
from .httpbase.task import DEFAULT_TIMEOUT
from skitai import was

class TaskBase (corequest):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, **meta):
        assert isinstance (reqs, (list, tuple))
        self._timeout = timeout                
        self._reqs = reqs
        self.meta = meta

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

    def then (self, func):
        return Futures (self._reqs, self._timeout, **self.meta).then (func)

    #------------------------------------------------------
    def cache (self, cache = 60, cache_if = (200,)):
        [r.cache (cache, cache_if) for r in self.results]

    def dispatch (self, cache = None, cache_if = (200,), timeout = None):
        return [req.dispatch (cache, cache_if, timeout or self._timeout) for req in self._reqs]
        
    def wait (self, timeout = None):
        return [req.wait (timeout or self._timeout) for req in self._reqs]
        
    def commit (self, timeout = None):
        [req.commit (timeout or self._timeout) for req in self._reqs] 
    
    def fetch (self, cache = None, cache_if = (200,)):
        return [req.fetch (cache, cache_if) for req in self._reqs]
        
    def one (self, cache = None, cache_if = (200,), timeout = None):
        return [req.one (cache, cache_if) for req in self._reqs]


class Mask (response, TaskBase):
    def __init__ (self, data, _expt = None, **meta):
        self._expt = _expt
        self._data = data
        self.meta = meta

    def _reraise (self):
        if self._expt:
            raise self._expt

    def commit (self):
        self._reraise ()

    def fetch (self):
        self._reraise ()
        return self._data
    
    def one (self):    
        self._reraise ()
        if len (self._data) == 0:
            raise HTTPError ("404 Not Found")
        if len (self._data) != 1:
            raise HTTPError ("409 Conflict")
        if isinstance (self._data, dict):
            return self._data.popitem () [1]
        return self._data [0]


class CompletedTasks (response, Tasks):
    def __init__ (self, reqs, **meta):
        Tasks.__init__ (self, reqs, **meta)


class Futures (TaskBase):
    def __init__ (self, reqs, timeout = 10, **meta):
        TaskBase.__init__ (self, reqs, timeout, **meta)
        self._was = None       
        self._fulfilled = None
        self._responded = 0
            
    def then (self, func):        
        self._fulfilled = func
        try: self._was = was._clone (True)
        except TypeError: pass               
        for reqid, req in enumerate (self._reqs):
           req.set_callback (self._collect, reqid, self._timeout)
        return self

    def returning (self, returning):
        return returning

    def _collect (self, res):
        self._responded += 1        
        if self._responded == len (self._reqs):
            if self._fulfilled:             
                self._respond ()
            else:
                self._was.response ("205 No Content", "")
                self._was.response.done ()
            
    def _respond (self):
        response = self._was.response         
        try:
            tasks = CompletedTasks (self._reqs, **self.meta)
            content = self._fulfilled (self._was, tasks)
            will_be_push = make_pushables (response, content)
            content = None
        except MemoryError:
            raise
        except HTTPError as e:
            response.start_response (e.status)
            content = response.build_error_template (e.explain, e.errno, was = self._was)
        except:            
            self._was.traceback ()
            response.start_response ("502 Bad Gateway")
            content = response.build_error_template (self._was.app.debug and sys.exc_info () or None, 0, was = self._was)            
       
        if content:
           will_be_push = make_pushables (response, content)
        
        if will_be_push is None:
            return
           
        for part in will_be_push:
            if len (will_be_push) == 1 and type (part) is bytes and len (response) == 0:
                response.update ("Content-Length", len (part))
            response.push (part)                
        response.done ()


class Future (Futures):
    def __init__ (self, req, timeout, **meta):
        Futures.__init__ (self, [req], timeout, **meta)
