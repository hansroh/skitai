import time

class Handler:
	def __init__ (self, wasc, realm, proxypass_handler):
		self.wasc = wasc
		self.realm = realm
		self.proxypass_handler = proxypass_handler
		self.ts = None
		#self.ts = {"1234": ("hansroh", ["admin"], 0)}
		
	def set_token_storage (self, storage):
		self.ts = storage		
	
	def set_error (self, request, error = "", desciption = ""):		
		if error:
			request.response ["WWW-Authenticate"] = 'Bearer realm="%s", error="%s", error_description="%s"' % (self.realm, error, desciption)
		else:
			request.response ["WWW-Authenticate"] = 'Bearer realm="%s"' % self.realm
		
	def match (self, request):
		if self.proxypass_handler.match (request):
			return 1
		return 0
			
	def handle_request (self, request):
		if self.ts is None:
			self.set_error (request, "token_storage_error", "Token storage not exists")
			return request.response.abort (500)

		authorization = request.get_header ("authorization")
		if not authorization or authorization[:7].lower () != "bearer ":
			self.set_error (request)
			return request.response.abort (401)
		
		token = authorization [7:]
		try:
			self.ts.get (token, request, self.continue_request)
		except TypeError: # no callback
			credinfo = self.ts.get (token)
			self.continue_request (request, credinfo)	
		
	def continue_request (self, request, credinfo):
		if credinfo is None:
			self.set_error (request, "invalid_token", "The access token not exists")
			return request.response.abort (401)
			
		user, roles, expires = credinfo
		if expires and expires > time.time ():
			self.set_error (request, "invalid_token", "The access token expired")
			return request.response.abort (401)
			
		cluster = self.proxypass_handler.find_cluster (request)[0]
		if not cluster.has_permission (request, roles):
			self.set_error (request, "insufficient_scope", "The access token is not valid")
			return request.response.abort (403)
		
		self.proxypass_handler.handle_request (request)
		
