import sys
from ..utility import make_pushables
from ..exceptions import HTTPError
from ..coops.rpc.cluster_dist_call import DEFAULT_TIMEOUT
from skitai import was
from ..corequest import corequest, response

class TaskBase (corequest):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, **args):
        assert isinstance (reqs, (list, tuple))
        self.timeout = timeout                
        self.reqs = reqs
        self.ARGS = args

    def __getattr__ (self, name):
        try:
            return self.ARGS [name]
        except KeyError:
            raise AttributeError ("{} cannot found".format (name))    

class Tasks (TaskBase):
    def __init__ (self, reqs, timeout = DEFAULT_TIMEOUT, **args):
        TaskBase.__init__ (self, reqs, timeout, **args)
        self._results = []        

    def __iter__ (self):
        return iter (self.reqs)
    
    def __getitem__ (self, sliced):
        return self.reqs [sliced].dispatch ()
    
    def add (self, req):
        self.reqs.append (req)

    def merge (self, tasks):
        for req in tasks.reqs:
            self.add (req)        

    def then (self, func, **kargs):
        return was.Futures (self.reqs, self.timeout).then (func, **kargs)

    #------------------------------------------------------
    def cache (self, cache = 60, cache_if = (200,)):
        [r.cache (cache, cache_if) for r in self.results]

    def dispatch (self, cache = None, cache_if = (200,), timeout = None):
        return [req.dispatch (cache, cache_if, timeout or self.timeout) for req in self.reqs]
        
    def wait (self, timeout = None):
        return [req.wait (timeout or self.timeout) for req in self.reqs]
        
    def commit (self, timeout = None):
        [req.commit (timeout or self.timeout) for req in self.reqs] 
    
    def fetch (self, cache = None, cache_if = (200,)):
        return [req.fetch (cache, cache_if) for req in self.reqs]
        
    def one (self, cache = None, cache_if = (200,), timeout = None):
        return [req.one (cache, cache_if) for req in self.reqs]


class Mask (response):
    def __init__ (self, data):
        self._data = data

    def fetch (self):
        return self._data
    one = fetch


class CompletedTasks (response, Tasks):
    def __init__ (self, reqs, **args):
        Tasks.__init__ (self, reqs, **args)


class Futures (TaskBase):
    def __init__ (self, was, reqs, timeout = 10, **args):
        TaskBase.__init__ (self, reqs, timeout, **args)
        self._was = was        
        self.fulfilled = None
        self.responded = 0        
            
    def then (self, func, **kargs):
        self.ARGS.update (kargs)
        self.fulfilled = func
        for reqid, req in enumerate (self.reqs):
           req.set_callback (self._collect, reqid, self.timeout)
        return self
                 
    def _collect (self, res):
        self.responded += 1        
        if self.responded == len (self.reqs):
            if self.fulfilled:             
                self.respond ()
            else:
                self._was.response ("205 No Content", "")
                self._was.response.done ()
            
    def respond (self):
        response = self._was.response         
        try:
            tasks = CompletedTasks (self.reqs, **self.ARGS)
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
    
