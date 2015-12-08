from . import ssgi_handler

class Handler (ssgi_handler.Handler):
	def __init__(self, wasc):
		self.wasc = wasc		
		
	def match (self, request):
		return request.split_uri() [0] == "/ping"
		
	def handle_request (self, request):
		# WSGI emulating
		env = self.build_environ (request)
		start_response = request.response.start_response
		
		start_response ("200 OK")
		request.response ["Content-Type"] = "text/plain"
		request.response ["Content-Length"] = "4"
		request.response.push (b"pong")
		request.response.done ()
		