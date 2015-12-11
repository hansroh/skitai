from . import wsgi_executor
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib


class Executor (wsgi_executor.Executor):
	def __call__ (self):
		data = self.env ["wsgi.input"].read ()	
					
		args, methodname = xmlrpclib.loads (data)
		if methodname != "system.multicall":
			thunks = [(methodname, args)]
		else:
			thunks = []
			for _methodname, _args in [(each ["methodName"], each ["params"]) for each in args]:
				thunks.append ((methodname, _args))
		
		results = []
		for _method, _args in thunks:
			path_info = self.env ["PATH_INFO"] = "/" + _method.replace (".", "/")
			thing, param = self.get_method (path_info)
			if not thing or param == 301:
				results.append (xmlrpclib.Fault (404, "Method Not Found"))
				continue							
			try:
				result = self.generate_content (thing, param)				
			except:
				results.append (xmlrpclib.Fault (500, wsgi_executor.traceback ()))
			else:
				results.append (result)
		
		self.commit ()
		
		if len (results) == 1: results = tuple (results)
		else: results = (results,)
			
		return xmlrpclib.dumps (results, methodresponse = True, allow_none = True, encoding = "utf8").encoding ("utf8")
		
