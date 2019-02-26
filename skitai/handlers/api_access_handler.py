import time
from rs4 import jwt

class AuthorizedUser:
	def __init__ (self, user, roles, realm):
		self.name = user	
		self.roles = roles
		self.realm = realm
		
class Handler:
	def __init__ (self, wasc, authenticate, realm, proxypass_handler, secret_key = None):
		self.wasc = wasc
		self.authenticate = authenticate
		self.realm = realm
		self.proxypass_handler = proxypass_handler
		self.secret_key = secret_key
		if type (self.secret_key) is str:
			self.secret_key = self.secret_key.encode ("utf8")
		self.auth_handler = None
		
	def set_auth_handler (self, handler):
		self.auth_handler = handler
	
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
		if not self.authenticate:
			return self.continue_request (request)
		
		authorization = request.get_header ("authorization")
		if not authorization or authorization[:7].lower () != "bearer ":
			self.set_error (request)
			return request.response.error (401)
		
		token = authorization [7:]	
		if not self.secret_key:
			self.set_error (request, "secret_key_error", "Secret key error")
			return request.response.error (500)
		claim = jwt.get_claim (self.secret_key, token)
		if not claim:
			self.set_error (request, "invalid_token", "The access token invalid")
			return request.response.error (401)			
		request.token = token.split (".")[1]
		if self.auth_handler:					
			request.claim = claim
			self.auth_handler (self, request)					
		else:
			self.continue_request (request, claim.get ("user"), claim.get ("roles"))
		
	def continue_request (self, request, username = None, roles = None):
		if self.authenticate:			
			request.user = AuthorizedUser (username, roles, self.realm)
			if not roles:
				self.set_error (request, "invalid_token", "The access token not exists")
				return request.response.error (401)
			
			cluster = self.proxypass_handler.find_cluster (request)[0]
			if not cluster.has_permission (request, roles):
				self.set_error (request, "insufficient_scope", "The access token is not valid")
				return request.response.error (403)
	
		self.proxypass_handler.handle_request (request)
		