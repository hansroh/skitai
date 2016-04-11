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
			for _methodname, _args in [(each ["methodName"], each ["params"]) for each in args [0]]:
				thunks.append ((_methodname, _args))
		
		self.build_was ()
		
		results = []
		for _method, _args in thunks:
			path_info = self.env ["PATH_INFO"] = "/" + _method.replace (".", "/")
			current_app, thing, param = self.get_method (path_info)
			self.was.subapp = current_app
			if not thing or param == 301:
				try: raise Exception('Method "%s" is not supported' % _method)
				except: results.append ({'faultCode' : 1, 'faultString' : wsgi_executor.traceback ()})
				continue

			try:
				result = self.generate_content (thing, _args, {})
			except:
				results.append ({'faultCode' : 1, 'faultString' : self.was.app.debug and wsgi_executor.traceback () or "Error Occured"})
			else:
				results.append ((result [0],))
			del self.was.subapp
		
		if methodname != "system.multicall": results = results [0]
		else: results = (results,)
		
		self.commit ()
		self.was.response ["Content-Type"] = "text/xml"
		
		del self.was.env		
		return xmlrpclib.dumps (results, methodresponse = True, allow_none = True, encoding = "utf8").encode ("utf8")
		
