
class Futures:
    def __init__ (self, wasc, request, app, env, *reqs, **args):
        self.wasc = wasc
        self.request = request
        self.env = env
        self.app = self.app
        
        self.reqs = reqs
        self.args = args
        
    