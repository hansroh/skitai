
class Handler:
	def __init__(self, wasc):
		self.wasc = wasc
		self.code = 404
		
	def match (self, request):
		exists_resource = self.wasc.apps.has_route (request.split_uri() [0])
		
		if exists_resource == 0:
			self.code = 404
			return 1
		elif exists_resource == -1:
			self.code = 301
			return 1
		else:
			self.code = 200	
			
		if request.command == "head":
			return 1
		return 0
		
	def handle_request (self, request):
		if self.code == 301:			
			request.response ["Location"] = "%s/" % request.uri
					
		if request.command == "head":
			request.response.reply (self.code)
			request.response.done ()
		else:	
			request.response.error (self.code)

