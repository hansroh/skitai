import sys
from ..utility import make_pushables
from ..exceptions import HTTPError
from ..rpc.cluster_dist_call import DEFAULT_TIMEOUT
from skitai import was
from ..corequest import corequest

class TaskBase (corequest):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, cache_timeout = 0, cache_if = (200,)):
        assert isinstance (reqs, (list, tuple))        
        self.timeout = timeout        
        self.cache_timeout = cache_timeout
        self.cache_if = cache_if
        self.reqs = reqs        


class Tasks (TaskBase):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, cache_timeout = 0, cache_if = (200,)):
        TaskBase.__init__ (self, reqs, timeout, cache_timeout, cache_if)
        self._results = []
        self._data = []
        
    def __iter__ (self):
        return iter (self.results)
    
    def __getitem__ (self, sliced):
        return self.results [sliced]

    @property
    def results (self):       
        return self._results or self.dispatch ()
    
    def then (self, func, timeout = None, **kargs):
        return was.Futures (self.reqs, timeout or self.timeout).then (func, **kargs)

    def dispatch (self):
        self._results = [req.dispatch (self.timeout, self.cache_timeout, self.cache_if) for req in self.reqs]
        return self._results 
    
    def wait (self):
        self._results = [req.wait (self.timeout) for req in self.reqs]

    def fetch (self):
        if self._data:
            return self._data
        self._data = [r.fetch () for r in self.results]
        return self._data

    def one (self):
        if self._data:
            return self._data
        self._data = [r.one () for r in self.results]
        return self._data

    def commit (self):
        self._results = [req.commit (self.timeout) for req in self.reqs] 
    
    def cache (self, cache = 60, cache_if = (200,)):
        [r.cache (cache, cache_if) for r in self.results]
        

class CompletedTasks (Tasks):
    def __init__ (self, rss, timeout = 10, cache_timeout = 0, cache_if = (200,)):
        TaskBase.__init__ (self, [], timeout, cache_timeout, cache_if)
        self._results = rss
        self._data = []


class Futures (TaskBase):
    def __init__ (self, was, reqs, timeout = 10, cache_timeout = 0, cache_if = (200,)):
        TaskBase.__init__ (self, reqs, timeout, cache_timeout, cache_if)
        self._was = was
        self.args = {}
        self.fulfilled = None
        self.responded = 0        
        self.ress = [None] * len (self.reqs)
            
    def then (self, func, **kargs):
        self.args = kargs
        self.fulfilled = func
        for reqid, req in enumerate (self.reqs):            
            req.set_callback (self._collect, reqid, self.timeout)
        return self
                 
    def _collect (self, res):
        self.responded += 1
        reqid = res.meta ["__reqid"]
        self.ress [reqid] = res
        self.cache_timeout and res.cache (self.cache_timeout, self.cache_if)
        if self.responded == len (self.reqs):
            if self.fulfilled:             
                self.respond ()
            else:
                self._was.response ("205 No Content", "")
                self._was.response.done ()
            
    def respond (self):
        response = self._was.response         
        try:
            tasks = CompletedTasks (self.ress, self.timeout, self.cache_timeout, self.cache_if)
            if self.args:
                content = self.fulfilled (self._was, tasks, **self.args)
            else:
                content = self.fulfilled (self._was, tasks)
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
    
