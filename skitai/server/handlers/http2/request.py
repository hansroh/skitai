from skitai.server import http_request
from .response import response

class request (http_request.http_request):
	def __init__ (self, *args):
		self.request_number = self.request_count.inc()		
		(self.http2, self.channel, self.request,		 
		 self.command, self.uri, self.version, self.scheme,
		 self.header, self.stream_id, self.is_promise) = args
		
		self.logger = self.channel.server.server_logger
		self.server_ident = self.channel.server.SERVER_IDENT
		self.body = None
		self.reply_code = 200
		self.reply_message = ""		
		self._split_uri = None
		self._header_cache = {}
		self.gzip_encoded = False
		
		self.outgoing_producer = None
		self.depends_on = 0
		self.weight = 0
				
		self.response = response (self)
	
	def get_scheme (self):	
		return self.scheme
		

