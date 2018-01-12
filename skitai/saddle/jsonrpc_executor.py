from . import xmlrpc_executor
try:
	import jsonrpclib
except ImportError:
	pass

class Executor (xmlrpc_executor.Executor):
	
	def __call__ (self):
		request = self.env ["skitai.was"].request		
		data = self.env ["wsgi.input"].read ()
		args = jsonrpclib.loads (data)

		is_multicall = False		
		jsonrpc = "2.0"		
		if isinstance (args, dict):
			thunks = [(args ["method"], args.get ("params", []), args ["id"], args ["jsonrpc"])]						
		else:
			is_multicall = True
			thunks = []
			for each in args:
				thunks.append ((each ["method"], each.get ("params", []), each ['id'], each ['jsonrpc']))
				
		self.build_was ()				
		results = []		
		for _method, _args, _rpcid, _jsonrpc in thunks:
			path_info = self.env ["PATH_INFO"] = "/" + _method.replace (".", "/")						
			current_app, thing, param, respcode = self.find_method (request, path_info, is_multicall is False)
			if respcode:				
				results.append (jsonrpclib.dumps (jsonrpclib.Fault (-32000, self.get_http_error_message (respcode), rpcid = _rpcid)))
				continue
				
			self.was.subapp = current_app
			try:
				result = self.chained_exec (thing, _args, {})
			except:			   
				results.append (jsonrpclib.dumps (jsonrpclib.Fault (-32000, self.get_traceback (), rpcid = _rpcid)))
			else:
				results.append (jsonrpclib.dumps (result, methodresponse = True, rpcid = _rpcid, version = _jsonrpc))
			del self.was.subapp
		
		self.was.response ["Content-Type"] = "application/json-rpc"
		self.commit ()
		del self.was.env   
		
		return is_multicall and  ("[" + ",".join (results) + "]") or results [0]
		