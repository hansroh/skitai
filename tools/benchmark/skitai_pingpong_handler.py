"""
This module is copy of skitai.handler.pingpong_handler.py.
It's not actually used by skitai, but for just your reference
"""

from . import wsgi_handler

class Handler (wsgi_handler.Handler):
	def __init__(self, wasc):
		self.wasc = wasc		
		
	def match (self, request):
		return request.split_uri() [0] == "/ping"
		
	def handle_request (self, request):
		# WSGI Server Payload Emulating
		env = self.build_environ (request)
		start_response = request.response.start_response
		
		start_response ("200 OK", [("Content-Type", "text/plain"), ("Content-Length", "4")])
		request.response.push (b"pong")
		request.response.done ()
		