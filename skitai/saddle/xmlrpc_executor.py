from . import wsgi_executor
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
from aquests.protocols.http import respcodes

class Executor (wsgi_executor.Executor):
	
	def get_traceback (self):	
		msg = "HTTP Error: 500 Internal Server Error"
		if self.was.app.debug:
			msg += ", Traceback " + wsgi_executor.traceback ()
		return msg
	
	def get_http_error_message (self, respcode):	
		return "HTTP Error: {} {}".format (respcode, respcodes.get (respcode, "Undefined Error"))	

	def __call__ (self):
		request = self.env ["skitai.was"].request		
		data = self.env ["wsgi.input"].read ()
		args, methodname = xmlrpclib.loads (data)
		
		is_multicall = False
		if methodname != "system.multicall":
			thunks = [(methodname, args)]
		else:
			is_multicall = True
			thunks = []
			for _methodname, _args in [(each ["methodName"], each ["params"]) for each in args [0]]:
				thunks.append ((_methodname, _args))
		
		self.build_was ()
		results = []
		for _method, _args in thunks:
			path_info = self.env ["PATH_INFO"] = "/" + _method.replace (".", "/")						
			current_app, thing, param, respcode = self.find_method (request, path_info, is_multicall is False)			
			if respcode:
				results.append (xmlrpclib.Fault (1, self.get_http_error_message (respcode)))
				continue
				
			self.was.subapp = current_app
			try:
				result = self.chained_exec (thing, _args, {})
			except:
				results.append (xmlrpclib.Fault (1, self.get_traceback()))
			else:
				results.append ((result,))
			del self.was.subapp
		
		self.was.response ["Content-Type"] = "text/xml"
		self.commit ()
		del self.was.env
		
		results = is_multicall and (results,) or results [0] 			
		return xmlrpclib.dumps (results, methodresponse = True, allow_none = True, encoding = "utf8").encode ("utf8")
		
