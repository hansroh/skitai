import sys, os
import urllib.request, urllib.parse, urllib.error
import sys
from skitai.server import utility
from skitai.server.threads import trigger
from . import xmlrpc_handler
import jsonrpclib
from . import ssgi_handler


class Handler (xmlrpc_handler.Handler):
	GATEWAY_INTERFACE = 'JSONRPC/2.0'
	def match (self, request):
		if request.uri[:10].lower() == '/rpc3/' or (request.command == "post" and request.get_header ("content-type").startswith ("application/json-rpc")):
				return 1
		return 0
	
	def continue_request (self, request, data = None):
		ismulticall = False		
		rpcid = request.request_number
		jsonrpc = "2.0"
		path = ""
					
		try:
			if data:
				args = jsonrpclib.loads (data)
				if type (args) == type ([]):
					ismulticall = True
					
				else:
					methodname = args ["method"]
					path = "/" + methodname.replace (".", "/")
					rpcid = args ["id"]
					jsonrpc = args ["jsonrpc"]
					args = args.get ("params", [])
					
			else:
				path, params, query, fragment = request.split_uri()
				path = path[8:]
				args = utility.crack_query (query)			
		
		except:
			self.wasc.logger.trace ("server", request.uri)
			return request.response.error (400)
		
		method, app = None, None
		if not ismulticall:
			try:
				method, app = self.wasc.apps.get_app (path)
			except:
				self.wasc.logger.trace ("server", request.uri)
				return request.response.error (400)				
			if not method: return request.response.error (404)
			if not self.has_permission (request, app): return				
		
		try:
			was = self.create_was (request, app)
				
		except:
			self.wasc.logger.trace ("server", path)
			return request.response.error (500, catch (1))
		
		if self.use_thread:
			self.wasc.queue.put (Job (was, path, method, args, rpcid, jsonrpc, ismulticall))
		else:
			Job (was, path, method, args, rpcid, jsonrpc, ismulticall) ()
			
class Job (xmlrpc_handler.Job):
	def __init__ (self, was, muri, method, args, rpcid, jsonrpc, ismulticall):
		xmlrpc_handler.Job.__init__ (self, was, muri, method, args, ismulticall)
		self.rpcid = rpcid
		self.jsonrpc = jsonrpc
	
	def handle_error (self, code, msg, rpcid, jsonrpc):
		if self.was.request.command == "get":
			self.responses = None
			trigger.wakeup (lambda p=self.was.response, c=code, m=msg: (p.error (c, m),))
		else:
			self.responses.append (jsonrpclib.dumps (jsonrpclib.Fault (500, msg), rpcid = rpcid, version = jsonrpc))
	
	def call (self, method, args, rpcid, jsonrpc):
		response = None
		try:
			response = self.get_response (method, args)			
		except MemoryError:
			raise				
		except:
			self.was.logger.trace ("app", str (self))
			self.handle_error (500, ssgi_handler.catch(self.was.request.command == "get"), rpcid, jsonrpc)

		else:
			response = jsonrpclib.dumps (response, methodresponse = True, 
				encoding = "Encoding" in self.was.request.response and self.was.requestresponse ["Encoding"] or None, 
				rpcid = rpcid,	version = jsonrpc
			)
			self.responses.append (response)
	
	def itercall (self, path, args, rpcid, jsonrpc):
		try:
			method, app = self.was.apps.get_app (path)
			if not method:
				self.handle_error (404, "method not found", rpcid, jsonrpc)
				return
										
			elif not self.has_permission (app):
				self.handle_error (403, "You haven't permission for accessing this page", rpcid, jsonrpc)
				return
			
		except:
			self.was.logger.trace ("app", str (self))
			self.handle_error (500, ssgi_handler.catch(), rpcid, jsonrpc)
			return
							
		self.was.app = app
		self.call (method, args, rpcid, jsonrpc)
		
	def handle_response (self):
		try:
			if len (self.responses) == 1:
				response = self.responses [0]
			else:
				response = "[" + ",".join (self.responses) + "]"

		except:
			self.was.logger.trace ("app", str (self))
			self.handle_error (500, ssgi_handler.catch(self.was.request.command == "get"), rpcid, jsonrpc)
		
		else:
			try:
				self.commit_all ()
				self.was.request.response.update ('Content-Type', 'application/json-rpc')			
				self.was.request.response.update ('Content-Length', len (response))
				
			except:
				self.was.logger.trace ("server", str (self))
				self.handle_error (500, ssgi_handler.catch(self.was.request.command == "get"), rpcid, jsonrpc)
			
			else:
				trigger.wakeup (lambda p=self.was.response, d=response: (p.push(d), p.done()))
			
	def __call__(self):		
		if not self.ismulticall:
			self.call (self.method, self.args, self.rpcid, self.jsonrpc)
			
		else:
			for path, args, rpcid, jsonrpc in [( "/" + each ["method"].replace (".", "/"), each.get ("params", []), each ["id"], each ["jsonrpc"]) for each in self.args]:
				self.itercall (path, args, rpcid, jsonrpc)				
			
		if not self.was.response.is_sent_response and self.responses is not None:			
			self.handle_response ()
						
		self.dealloc ()
		
			
