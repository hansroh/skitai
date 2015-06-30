
class Handler:
	def __init__(self, wasc):
		self.wasc = wasc
		
	def match (self, request):
		if self.wasc.apps.has_route (request.uri) == 0:
			return 1
		return 0
		
	def handle_request (self, request):
		request.error (404)			
