from . import wsgi_executor
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
from skitai.server.http_response import http_response

class Executor (wsgi_executor.Executor):
	def __call__ (self):
		request = self.env ["skitai.was"].request
		
		data = self.env ["wsgi.input"].read ()
		args, methodname = xmlrpclib.loads (data)
		
		if methodname != "system.multicall":
			thunks = [(methodname, args)]
		else:
			thunks = []
			for _methodname, _args in [(each ["methodName"], each ["params"]) for each in args [0]]:
				thunks.append ((_methodname, _args))
		
		self.build_was ()
		
		results = []
		is_multicall = (methodname == "system.multicall")
		for _method, _args in thunks:
			path_info = self.env ["PATH_INFO"] = "/" + _method.replace (".", "/")						
			current_app, thing, param, respcode = self.find_method (request, path_info, is_multicall is False)			
			if respcode:
				results.append ({'faultCode' : 1, 'faultString' : http_response.responses.get (rescode, "Undefined")})
				
			self.was.subapp = current_app
			try:
				result = self.chained_exec (thing, _args, {})
			except:
				results.append ({'faultCode' : 1, 'faultString' : self.was.app.debug and wsgi_executor.traceback () or "Error Occured"})				
			else:
				results.append ((result [0],))
			del self.was.subapp
		
		if not is_multicall: 
			if respcode:
				self.was.response.set_status (respcode)
			results = results [0]
		else: 
			results = (results,)
		
		self.commit ()
		self.was.response ["Content-Type"] = "text/xml"
		
		del self.was.env	
		return xmlrpclib.dumps (results, methodresponse = True, allow_none = True, encoding = "utf8").encode ("utf8")
		
