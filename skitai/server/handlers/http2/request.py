from skitai.server import http_request
from .response import response
import time

class request (http_request.http_request):
	def __init__ (self, http2, scheme, stream_id, is_promise, *args):
		http_request.http_request.__init__ (self, *args)
		self.http2 = http2
		self.stream_id = stream_id
		self._is_promise = is_promise
		self.depends_on = 0
		self.weight = 0
		self._scheme = scheme
	
	def make_response (self):				
		self.response = response (self)
			
	def get_scheme (self):	
		return self._scheme
	
	