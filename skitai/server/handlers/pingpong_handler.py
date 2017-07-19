
class Handler:
	def match (self, request):
		return request.uri == "/ping"
		
	def handle_request (self, request):
		request.response.start_response ("200 OK", [("Content-Type", "text/plain"), ("Content-Length", "4")])
		request.response.push (b"pong")
		request.response.done ()
		