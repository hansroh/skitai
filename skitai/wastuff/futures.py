from ..utility import make_pushables
import sys

class Futures:
    def __init__ (self, was, reqs, **args):
        assert isinstance (reqs, (list, tuple))
        
        self._was = was
        self.reqs = reqs
        self.args = args
        self.fulfilled = None
        self.responded = 0        
        self.ress = [None] * len (self.reqs)
        
    def then (self, func):        
        self.fulfilled = func
        for reqid, req in enumerate (self.reqs):
            req.set_callback (self._collect, reqid)
        return self
             
    def _collect (self, res):
        self.responded += 1
        reqid = res.meta ["__reqid"]
        self.ress [reqid] = res        
        if self.responded == len (self.reqs):
            if self.fulfilled:             
                self.respond ()
            else:
                self._was.response ("205 No Content", "")
                self._was.response.done ()
            
    def respond (self):    
        response = self._was.response
        try:            
            if self.args:
                content = self.fulfilled (self._was, self.ress, **self.args)
            else:
                content = self.fulfilled (self._was, self.ress)    
            will_be_push = make_pushables (response, content, ignore_futrue = False)                            
        except MemoryError:
            raise
        except:            
            self._was.traceback ()
            response.error (508, "Application Error", self._was.app.debug and sys.exc_info () or None)            
        else:
            if will_be_push is None:
                return                        
            for part in will_be_push:
                if len (will_be_push) == 1 and type (part) is bytes and len (response) == 0:
                    response.update ("Content-Length", len (part))
                response.push (part)                
        response.done ()
