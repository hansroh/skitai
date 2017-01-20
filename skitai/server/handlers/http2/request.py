from skitai.server import http_request
from .response import response
import time

class request (http_request.http_request):
	def __init__ (self, http2, scheme, stream_id, is_promise, *args):
		http_request.http_request.__init__ (self, *args)
		self.http2 = http2
		self.scheme = scheme
		self.stream_id = stream_id
		self._is_promise = is_promise
		
<<<<<<< HEAD
		self.logger = self.channel.server.server_logger
		self.server_ident = self.channel.server.SERVER_IDENT
		self.body = None
		self.reply_code = 200
		self.reply_message = ""		
		self._split_uri = None
		self._header_cache = {}
		self.rbytes = 0
		self.loadbalance_retry = 0
		self.gzip_encoded = False		
		
		self.outgoing_producer = None
=======
		#self.outgoing_producer = None
>>>>>>> http2
		self.depends_on = 0
		self.weight = 0
	
	def make_response (self):				
		self.response = response (self)
			
	def get_scheme (self):	
		return self.scheme
	
	