import sys, os
import sys
from skitai.server import utility
from skitai.server.threads import trigger
from . import ssgi_handler
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
		
class Handler (ssgi_handler.Handler):
	GATEWAY_INTERFACE = 'XMLRPC/2.0'
	def match (self, request):
		if request.uri[:6].lower() == '/rpc2/' or (request.command == "post" and request.get_header ("content-type").startswith ("text/xml")):			
				return 1
		return 0
	
	def continue_request (self, request, data = None):
		ismulticall = False	
		try:
			if data:
				args, methodname = xmlrpc.client.loads (data)
				if methodname == "system.multicall":
					ismulticall = True
				path = "/" + methodname.replace (".", "/")
					
			else:
				path, params, query, fragment = request.split_uri()
				path = path[5:]
				args = utility.crack_query (query)
		
		except:
			self.wasc.logger.trace ("server", request.uri)
			return request.response.error (400)
		
		method, app = None, None
		if not ismulticall:
			try:
				method, app = self.wasc.apps.get_app (path)
				
			except:
				self.wasc.logger.trace ("server", path)
				return request.response.error (500, catch (1))
								
			if not method: return request.response.error (404)
			if not self.has_permission (request, app): return			
		
		try:
			was = self.create_was (request, app)				
		except:
			self.wasc.logger.trace ("server", path)
			return request.response.error (500, catch (1))
		
		if self.use_thread:
			self.wasc.queue.put (Job (was, path, method, args, ismulticall))
		else:	
			Job (was, path, method, args, ismulticall) ()
		
			
class Job (ssgi_handler.Job):
	def __init__ (self, was, muri, method, args, ismulticall):
		self.was = was
		self.muri = muri
		self.method = method
		self.args = args
		self.ismulticall = ismulticall
		self.responses = []
	
	def has_permission (self, app):
		if not app: return True
		permission = []
		try: 
			permission = app.permission
		except AttributeError: 
			return True
		if permission and not self.was.authorizer.has_permission (self.was.request, permission, push_error = 0): # request athorization
			return False
		return True
		
	def handle_error (self, code, msg = ""):
		if self.was.request.command == "get":
			self.responses = None
			trigger.wakeup (lambda p=self.was.response, c=code, m=msg: (p.error (c, m),))
		else:
			self.responses.append (xmlrpc.client.Fault (code, msg))
			
	def call (self, method, args):
		response = None
		try:			
			response = self.get_response (method, args)	
		except MemoryError:
			raise				
		except:
			self.was.logger.trace ("app", str (self))
			self.handle_error (500, ssgi_handler.catch(self.was.request.command == "get"))

		else:
			self.responses.append (response)
	
	def itercall (self, path, args):
		try:
			method, app = self.was.apps.get_app (path)
			if not method:
				self.handle_error (404, "method not found")
				return
										
			elif not self.has_permission (app):
				self.handle_error (403, "You haven't permission for accessing this page")
				return
			
		except:
			self.was.logger.trace ("app")
			self.handle_error (500, ssgi_handler.catch())
			return
							
		self.was.app = app	
		self.call (method, args)
		
	def handle_response (self):		
		try:
			if len (self.responses) == 1:
				fresp = tuple (self.responses)
			else:
				fresp = (self.responses,)	
			response = xmlrpc.client.dumps (fresp, methodresponse = True, allow_none = True, encoding = "Encoding" in self.was.request.response and self.was.request ["Encoding"] or None)
			
		except:
			self.was.logger.trace ("app")
			self.handle_error (500, ssgi_handler.catch(self.was.request.command == "get"))
		
		else:
			try:
				self.commit_all ()
				self.was.request.response.update ('Content-Type', 'text/xml')
				self.was.request.response.update ('Content-Length', len (response))
				
			except:
				self.was.logger.trace ("server")
				self.handle_error (500, ssgi_handler.catch(self.was.request.command == "get"))
			
			else:
				trigger.wakeup (lambda p=self.was.response, d=response: (p.push(d), p.done()))
					
	def __call__(self):
		if not self.ismulticall:
			self.call (self.method, self.args)
						
		else:
			for path, args in [("/" + each ["methodName"].replace (".", "/"), each ["params"]) for each in self.args [0]]:				
				self.itercall (path, args)
				
		if not self.was.response.is_sent_response and self.responses is not None:
			self.handle_response ()
			
		self.dealloc ()
		
			
