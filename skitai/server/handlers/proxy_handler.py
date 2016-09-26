from . import wsgi_handler
from skitai.protocol.http import request as http_request
from .proxy import POST_MAX_SIZE, UPLOAD_MAX_SIZE
from .proxy.collector import Collector
from .proxy.request_handler import ProxyRequestHandler

			
class Handler (wsgi_handler.Handler):
	def __init__ (self, wasc, clusters, cachefs = None):
		self.wasc = wasc
		self.clusters = clusters
		self.cachefs = cachefs
		#self.cachefs = None # DELETE IT!
		self.q = {}
				
	def match (self, request):
		uri = request.uri.lower ()
		if uri.startswith ("http://") or uri.startswith ("https://") or uri.startswith ("ws://") or uri.startswith ("wss://"):
			return 1
		if request.command == "connect":
			return 1
		return 0
		
	def handle_request (self, request):
		collector = None
		if request.command in ('post', 'put'):
			ct = request.get_header ("content-type")
			if not ct: ct = ""
			current_post_max_size = ct.startswith ("multipart/form-data") and UPLOAD_MAX_SIZE or POST_MAX_SIZE
			collector = self.make_collector (Collector, request, current_post_max_size)
			if collector:
				request.collector = collector
				collector.start_collect ()
			else:
				return # error was already called in make_collector ()							
		self.continue_request(request, collector)
					
	def continue_request (self, request, collector, asyncon = None):		
		if self.is_cached (request, collector is not None):
			return
		
		try:
			if asyncon is None:		
				if request.command == "connect":
					asyncon_key = "tunnel://" + request.uri + "/"
				else:
					asyncon_key = request.uri					
				asyncon = self.clusters ["__socketpool__"].get (asyncon_key)
					
			req = http_request.HTTPRequest (request.uri, request.command, collector is not None, logger = self.wasc.logger.get ("server"))				
			r = ProxyRequestHandler (asyncon, req, self.callback, request, collector)			
			if collector:
				collector.asyncon = asyncon
			r.start ()
						
		except:
			self.wasc.logger.trace ("server")			
			request.response.error (500, "", "Proxy request has been failed.")
		
	def is_cached (self, request, has_data):		
		if has_data:
			return False
		if request.get_header ("cookie") is not None:
			return False
		if request.get_header ("progma") == "no-cache" or request.get_header ("cache-control") == "no-cache":
			request.response ["X-Cache-Lookup"] = "PASSED"
			return False
		
		if self.cachefs:
			try:
				accept_encoding = request.get_header ("accept-encoding")
				hit, compressed, max_age, content_type, content = self.cachefs.get (request.uri, "", accept_encoding and accept_encoding.find ("gzip") != -1)
						
			except:
				self.wasc.logger.trace ("server")	
				return False
			
			else:
				if hit:
					if hit == 1:
						request.response ["X-Cache-Lookup"] = "MEM_HIT"
					else:
						request.response ["X-Cache-Lookup"] = "HIT"
					if content_type:
						request.response ["Content-Type"] = content_type					
					request.response ["Cache-Control"] = "max-age=%d" % max_age
					if compressed:
						request.response ["Content-Encoding"] = "gzip"
					request.response.push (content)
					request.response.done ()
					return True
					
		request.response ["X-Cache-Lookup"] = "MISS"
		return False
	
	def save_cache (self, request, handler):
		try:			
			if self.cachefs and handler.response.max_age:
				self.cachefs.save (
					request.uri, handler.request.data, 
					handler.response.get_header ("content-type"), handler.response.get_content (), 
					handler.response.max_age, request.response ["Content-Encoding"] == "gzip"
				)
				
		except:
			self.wasc.logger.trace ("server")
	
	def dealloc (self, request, handler):
		handler.callback = None				
		handler.response = None
		handler.collector = None
		request.collector = None
		request.producer = None
		request.response = None # break back ref.		
		del handler
			
	def callback (self, handler):
		response, request = handler.response, handler.client_request
		
		if request.channel:
			if response.code >= 700:
				request.response.error (506, response.msg)
			
			else:
				try:
					self.save_cache (request, handler)
				except:
					self.wasc.logger.trace ("server")
		
		self.dealloc (request, handler)
		