from atila import Atila
from skitai import was
import time

app = Atila (__name__)
app.debug = True
app.use_reloader = True

class Authorizer:
	def __init__ (self):
		self.tokens = {
			"12345678-1234-123456": ("hansroh", ["user", "admin"], 0)
		}
	
	def handle_user (self, response, handler, request):
		username, roles, expires = self.tokens.get (request.token)		
		if expires and expires < time.time ():
			return handler.continue_request (request)
		handler.continue_request (request, username, roles)
		 	
	# For Token
	def handle_token (self, handler, request):		
		token = request.token
		was.postgresql (
			"@postgres",
			callback = (self.handle_user, (handler, request))			
		).execute ("SELECT * FROM weather;")

	# For JWT Claim
	def handle_claim (self, handler, request):
		claim = request.claim		
		expires = claim.get ("expires", 0)
		if expires and expires < time.time ():
			return handler.continue_request (request)
		handler.continue_request (request, claim.get ("user"), claim.get ("roles"))
		
	
@app.startup
def startup (wasc):
	wasc.handler.set_auth_handler (Authorizer ())
	
@app.route ("/")
def index (was):
	return "<h1>Skitai App Engine: API Gateway</h1>"


if __name__ == "__main__":
	import skitai
	skitai.alias ("@pypi", skitai.PROTO_HTTP, "gall.dcinside.com")
	skitai.alias ("@postgres", skitai.DB_PGSQL, "127.0.0.1:5432/mydb/postgres/1111")
	skitai.mount ('/', app)
	skitai.mount ('/lb', '@pypi')
	skitai.enable_gateway (True, "8fa06210-e109-11e6-934f-001b216d6e71", "Skitai API Gateway")
	skitai.run (
		address = "0.0.0.0",
		port = 30371	
	)
	