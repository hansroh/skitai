import time

class Handler:
	def __init__ (self, wasc, cluster_finder):
		self.wasc = wasc
		self.cluster_finder = cluster_finder
		self.ts = None
		#self.ts = {"asdasd": ("hansroh", ["admin"], "", 0)}
		
	def set_token_storage (self, storage):
		self.ts = storage		
	
	def set_error (self, request, status, error = "", desciption = ""):		
		request.response.set_status (status)
		if error:
			request.response ["WWW-Authenticate"] = 'Bearer realm="API Gateway", error="%s", error_description="%s"' % (error, desciption)
		else:
			request.response ["WWW-Authenticate"] = 'Bearer realm="API Gateway"'
		
	def match (self, request):
		if self.ts is None:
			self.set_error (request, "500 Internal Server Error", "token_storage_error", "Token storage not exists")
			return 1

		authorization = request.get_header ("authorization")
		if not authorization or authorization[:7].lower () != "bearer ":
			self.set_error (request, "401 Unauthorized")
			return 1
		
		credinfo = self.ts.get (authorization [7:]) # token
		if credinfo is None:
			self.set_error (request, "401 Unauthorized", "invalid_token", "The access token not exists")
			return 1
			
		user, roles, realm, expires = credinfo
		if expires and expires > time.time ():
			self.set_error (request, "401 Unauthorized", "invalid_token", "The access token expired")
			return 1
			
		cluster = self.cluster_finder (request) [0]
		if not cluster:
			self.set_error (request, "404 Not Found", "api_not_found", "The requested API not exists")
			return 1
			
		if not cluster.has_permission (roles):
			self.set_error (request, "403 Forbidden", "insufficient_scope", "The access token is not valid")
			return 1
		
		return 0
		
	def handle_request (self, request):
		request.response.abort (request.response.reply_code, request.response.reply_message)
