from ..utility import make_pushables
import sys

class Futures:
    def __init__ (self, was, reqs, **args):
        assert isinstance (reqs, (list, tuple))
        self._was = was
        
        self.reqs = reqs
        self.ress = [None] * len (self.reqs)
        for reqid, req in enumerate (self.reqs):
            reg.set_callback (self._collect, reqid)
        self.args = args
        self.responded = 0        
    
    def then (self, func):
        self.fulfilled = func
        return self
             
    def _collect (self, res):
        self.responded += 1
        reqid = result.meta ["__reqid"]
        self.ress [reqid] = res
        if self.fulfilled and self.responded == len (self.ress):
            self.respond ()
            
    def respond (self):    
        response = self._was.response
        try:            
            content = self.fulfilled (self._was, self.ress)            
            will_be_push = make_pushables (response, content)                            
        except MemoryError:
            raise
        except:            
            self._was.traceback ()
            response.error (508, "Application Error", self._was.app.debug and sys.exc_info () or None)            
        else:
            if will_be_push is None:
                return
            will_be_push = make_pushables (response, content)            
            for part in will_be_push:
                if len (will_be_push) == 1 and type (part) is bytes and len (response) == 0:
                    response.update ("Content-Length", len (part))
                self.response.push (part)                
        response.done ()
