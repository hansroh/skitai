
class Handler:
	def __init__(self, wasc):
		self.wasc = wasc
		
	def match (self, request):
		if request.command == "options":
			return 1
		return 0
		
	def handle_request (self, request):
		request.response ["Allow"] = "GET,HEAD,POST,DELETE,PUT,OPTIONS"
		request.response.error (200)
