from ...backbone import http_request
from .response import response
import time

class request (http_request.http_request):
	response_class = response

	def __init__ (self, protocol, scheme, stream_id, *args):
		http_request.http_request.__init__ (self, *args)
		self.protocol = protocol
		self.stream_id = stream_id
		self.depends_on = 0
		self.weight = 0
		self._scheme = scheme
		self._is_promise = False
		if (
			self.version.startswith ("2.") and stream_id % 2 == 0 or
			self.version.startswith ("3.") and stream_id % 4 == 3
		):
			self._is_promise = True
			self.set_stream_ended ()

	def make_response (self):
		self.response = self.response_class (self)

	def get_scheme (self):
		return self._scheme
