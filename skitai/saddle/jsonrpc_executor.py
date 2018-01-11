from . import wsgi_executor
try:
    import jsonrpclib
except ImportError:
    pass
from aquests.protocols.http import respcodes

class Executor (wsgi_executor.Executor):    
    def __call__ (self):
        request = self.env ["skitai.was"].request
        
        data = self.env ["wsgi.input"].read ()
        args = jsonrpclib.loads (data)

        is_multicall = False        
        jsonrpc = "2.0"
        path = ""
        
        if type (args) == type ([]):
            is_multicall = True
            thunks = []
            for each in args:
                thunks.append ((each ["method"], each.get ("params", []), each ['id'], each ['jsonrpc']))
            
        else:
            thunks = [(args ["method"], args.get ("params", []), args ["id"], args ["jsonrpc"])]
                
        self.build_was ()
                
        results = []        
        for _method, _args, _rpcid, _jsonrpc in thunks:
            path_info = self.env ["PATH_INFO"] = "/" + _method.replace (".", "/")                        
            current_app, thing, param, respcode = self.find_method (request, path_info, is_multicall is False)            
            if respcode:                
                results.append (jsonrpclib.dumps (jsonrpclib.Fault (1, respcodes.get (respcode, "Undefined Error")), rpcid = _rpcid, version = _jsonrpc))
                
            self.was.subapp = current_app
            try:
                result = self.chained_exec (thing, _args, {})
            except:
                results.append (jsonrpclib.dumps (jsonrpclib.Fault (1, self.was.app.debug and wsgi_executor.traceback () or "Error Occured")))                
            else:
                result = jsonrpclib.dumps (
                    result, methodresponse = True,
                    rpcid = _rpcid, version = _jsonrpc
            )
            results.append (result)
            del self.was.subapp
        
        self.commit ()
        self.was.response ["Content-Type"] = "application/json-rpc"
        
        del self.was.env   
        if len (results) == 1:
            results = results [0]
        else:
            results = "[" + ",".join (results) + "]" 
        return results
    