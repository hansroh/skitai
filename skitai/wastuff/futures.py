
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
            self.fulfilled (self._was, self.ress)            
    