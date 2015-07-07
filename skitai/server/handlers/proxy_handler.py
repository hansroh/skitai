import ssgi_handler
import re
from skitai.server.rpc import http_request, http_response
from skitai.client import adns
from skitai.server import compressors, producers
try:
	import ssl_tunnel
except ImportError:
	ssl_tunnel = None	
import time

class CollectError (Exception): pass
	
class Response (http_response.Response):
	SIZE_LIMIT = 2**24
	
	def __init__ (self, request, header, accept_gzip, client_request, asyncon):		
		self.client_request = client_request
		self.asyncon = asyncon
		self.accept_gzip = accept_gzip		
		self.request = request
		header = header.split ("\r\n")
		self.response = header [0]
		self.header = header [1:]
		self._header_cache = {}
		self.flushed_time = 0
		self.client_request.producer = self
		self.version, self.code, self.msg = http_response.crack_response (self.response)
				
		self.size = 0
		self.got_all_data = False
		self.reqtype = "html"
		
		if self.client_request.get_header ("cookie"):
			self.max_age = 0
		else:	
			self.set_max_age ()			
				
		self.p, self.u = http_response.getfakeparser (cache = self.max_age)		
		self.set_decompressor ()
						
	def set_decompressor (self):
		self.decompressor = None
		self.gzip_compressed = False		
		content_encoding = self.get_header ("Content-Encoding")
			
		if content_encoding == "gzip":
			if self.accept_gzip:
				self.gzip_compressed = True
			else:	
				self.decompressor = compressors.GZipDecompressor ()
		
	def is_gzip_compressed (self):
		return self.gzip_compressed
	
	def abort (self):
		self.client_request.producer = None		
		try: self.u.data = []
		except AttributeError: pass
		self.asyncon.abort ()	
			
	def affluent (self):
		# if channel doesn't consume data, delay recv data		
		return len (self.u.data) < 1000
		
	def ready (self):
		# if exist consumable data or wait
		return len (self.u.data) or self.got_all_data
		
	def more (self):
		self.flushed_time = time.time ()
		return self.u.read ()
		

class Collector (ssgi_handler.Collector):
	# same as asyncon ac_in_buffer_size
	ac_in_buffer_size = 4096
	asyncon = None
	def __init__ (self, handler, request):
		self.handler = handler
		self.request = request
		self.data = []
		self.cached = False
		self.cache = []
		self.got_all_data = False
		self.length = 0 
		self.content_length = self.get_content_length ()
	
	def reuse_cache (self):
		self.data = self.cache + self.data
		self.cache = []
			
	def start_collect (self):	
		if self.content_length == 0:
			return self.found_terminator ()
			
		if self.content_length <= ssgi_handler.MAX_POST_SIZE: #5M
			self.cached = True
		
		self.request.channel.set_terminator (self.content_length)
	
	def abort (self):
		self.data = []
		self.cache = []
		self.request.collector = None
		if self.asyncon:
			self.asyncon.abort ()
				
	def collect_incoming_data (self, data):
		#print "proxy_handler.collector << %d" % len (data), id (self)
		self.length += len (data)
		self.data.append (data)

	def found_terminator (self):
		self.request.channel.set_terminator ('\r\n\r\n')
		self.got_all_data = True
		# don't request.collector = None => do it at callback ()
		# because this collector will be used in Request.continue_start() later
	
	def get_cache (self):
		return "".join (self.cache)
	
	def affluent (self):
		# if channel doesn't consume data, delay recv data		
		return len (self.data) < 1000
		
	def ready (self):
		return len (self.data) or self.got_all_data
	
	def more (self):
		if not self.data:
			return ""
						
		data = []
		tl = 0
		while self.data:
			tl += len (self.data [0])
			if tl > self.ac_in_buffer_size:
				break
			data.append (self.data.pop (0))
		if self.cached:
			self.cache += data
		
		#print "proxy_handler.collector.more >> %d" % tl, id (self)
		return "".join (data)
		

class Request (http_request.Request):
	def __init__ (self, asyncon, request, callback, client_request, collector, connection = "keep-alive"):
		http_request.Request.__init__ (self, asyncon, request, callback, "1.1", connection)
		self.collector = collector
		self.client_request = client_request
		self.is_pushed_response = False
			
	def add_reply_headers (self):
		for line in self.response.get_headers ():
			try: k, v = line.split (": ", 1)
			except:	continue
			ll = k.lower ()
			if ll in ("expires", "date", "vary", "connection", "keep-alive", "content-length", "transfer-encoding", "content-encoding", "age"):
				continue
			self.client_request.response [k] = v.strip ()
	
	def push_response (self):		
		if self.is_pushed_response or not self.client_request.channel:
			return
		self.client_request.response.push (self.response)
		self.client_request.response.done (globbing = False, compress = False)
		self.is_pushed_response = True
			
	def done (self, error, msg = ""):
		# unbind readable/writable methods
		self.asyncon.ready = None
		self.asyncon.affluent = None		
		if self.client_request.channel:			
			self.client_request.channel.ready = None
			self.client_request.channel.affluent = None
		else:
			return

		# handle abnormally raised exceptions like network error etc.
		error, msg = self.recalibrate_response (error, msg)
		# finally, push response, but do not bind ready func because all data had been recieved.
		if not error:
			self.push_response ()
		
		if self.asyncon:
			self.asyncon.request = None
							
		if self.callback:
			self.callback (self)
			
	def collect_incoming_data (self, data):
		http_request.Request.collect_incoming_data (self, data)
		
	def is_continue_response (self):
		if self.response.code == 100 and self.client_request.get_header ("Expect") != "100-continue":
			# ignore, wait next message
			# if expect header exist on client, it's treated normal response
			self.response = None
			self.asyncon.set_terminator ("\r\n\r\n")
			return True
		return False
			
	def create_response (self):
		#print "#################################"
		#print self.buffer
		#print "---------------------------------"		
		
		if not self.client_request.channel:
			return
				
		buffer, self.buffer = self.buffer, ""		
		accept_gzip = ""
		accept_encoding = self.client_request.get_header ("Accept-Encoding")
		if accept_encoding and accept_encoding.find ("gzip") != -1:
			accept_gzip = "gzip"
		
		try:
			self.response = Response (self.request, buffer, accept_gzip, self.client_request, self.asyncon)
		except:
			self.log ("response header error: `%s`" % repr (buffer [:80]), "error")
			raise
		
		if self.is_continue_response ():
			# maybe response code is 100 continue
			return
		
		self.client_request.response.start (self.response.code, self.response.msg)
		self.add_reply_headers ()
		
		if self.response.is_gzip_compressed ():
			self.client_request.response ["Content-Encoding"] = "gzip"
	
		# in relay mode, possibly delayed
		self.client_request.channel.ready = self.response.ready
		self.asyncon.affluent = self.response.affluent
		
		self.push_response ()
	
	def continue_start (self, answer):
		if not answer:
			self.log ("DNS not found - %s" % self.asyncon.address [0], "error")
			return self.done (20, "DNS Not Found")
		
		if not self.client_request.channel:
			return
		
		self.asyncon.push (self.get_request_buffer ())
		if self.collector:
			self.push_collector ()
		self.asyncon.start_request (self)
	
	def retry (self):
		if self.retry_count: 
			return False
		if self.collector and not self.collector.cached:
			return False
		if not self.client_request.channel:
			return False
		
		self.asyncon.request = None # unlink back ref.		
		self.retry_count = 1
		
		self.asyncon.push (self.get_request_buffer ())
		if self.collector:
			self.collector.reuse_cache ()
			self.push_collector ()
		self.asyncon.start_request (self)
		return True
	
	def push_collector (self):
		if not self.collector.got_all_data:
			self.asyncon.ready = self.collector.ready
			self.client_request.channel.affluent = self.collector.affluent		
			# don't init_send cause of producer has no data yet
		self.asyncon.push_with_producer (self.collector, init_send = False)
								
	def get_request_buffer (self):
		data = self.request.get_data ()
		hc = {}
		
		if self.asyncon.address [1] in (80, 443):
			hc ["Host"] = "%s" % self.asyncon.address [0]
		else:
			hc ["Host"] = "%s:%d" % self.asyncon.address
			
		hc ["Connection"] = self.connection
		hc ["Accept-Encoding"] = "gzip"
		
		method = self.request.get_method ()			
		additional_headers = self.client_request.get_headers ()
		
		if additional_headers:
			for line in additional_headers:
				k, v = line.split (": ", 1)
				ll = k.lower ()
				if ll in ("connection", "keep-alive", "accept-encoding", "host"):
					continue
				hc [k] = v
				
		hc ["X-Forwarded-For"] = "%s" % self.client_request.get_remote_addr ()
				
		req = "%s %s HTTP/%s\r\n%s\r\n\r\n" % (
			method,
			self.request.url,
			self.http_version,
			"\r\n".join (map (lambda x: "%s: %s" % x, hc.items ()))			
		)
		
		#print "#################################"
		#print req
		#print "---------------------------------"
		return req

			
class Handler (ssgi_handler.Handler):
	def __init__ (self, wasc, clusters, cachefs = None):
		self.wasc = wasc
		self.clusters = clusters
		self.cachefs = cachefs
		#self.cachefs = None # DELETE IT!
		adns.init (self.wasc.logger.get ("server"))
				
	def match (self, request):		
		uri = request.uri.lower ()
		if uri.startswith ("http://") or uri.startswith ("https://"):
			return 1
		if request.command == "connect":
			return 1
		return 0
	
	def handle_request (self, request):
		if request.command == "connect":
			request.response.error (405)
			# GIVE UP :-(
			#ssl_tunnel.AsynSSLConnect (request, self.wasc.logger.get ("server"))
		
		else:
			collector = None
			if request.command in ('post', 'put'):
				ct = request.get_header ("content-type")
				if not ct: ct = ""
				post_max_size = ct.startswith ("multipart/form-data") and ssgi_handler.MAX_UPLOAD_SIZE or ssgi_handler.MAX_POST_SIZE
				collector = self.make_collector (Collector, request, post_max_size)
				if collector:
					request.collector = collector
					collector.start_collect ()					
				else:
					return # not allowed
								
			self.continue_request(request, collector)			
					
	def continue_request (self, request, collector):	
		request.response ["Proxy-Agent"] = "sae-asynconnect"
		
		if self.is_cached (request, collector is not None):
			return
		
		try:
			req = http_request.HTTPRequest (request.uri, request.command, collector is not None, logger = self.wasc.logger.get ("server"))		
			asyncon = self.clusters ["__socketpool__"].get (request.uri)
			r = Request (asyncon, req, self.callback, request, collector)			
			if collector:
				collector.asyncon = asyncon
			r.start ()
			
		except:
			self.wasc.logger.trace ("server")	
			request.response.error (500, ssgi_handler.catch (1))
	
	def is_cached (self, request, has_data):
		if has_data:
			return False
		if request.get_header ("cookie") is not None:
			return False
		if request.get_header ("progma") == "no-cache" or request.get_header ("cache-control") == "no-cache":
			request.response ["X-Cache-Lookup"] = "PASSED from bws"
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
						request.response ["X-Cache-Lookup"] = "MEM_HIT from bws"
					else:
						request.response ["X-Cache-Lookup"] = "HIT from bws"
					if content_type:
						request.response ["Content-Type"] = content_type					
					request.response ["Cache-Control"] = "max-age=%d" % max_age
					if compressed:
						request.response ["Content-Encoding"] = "gzip"
					request.response.push (content)
					request.response.done ()
					return True
					
		request.response ["X-Cache-Lookup"] = "MISS from bws"
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
		
		if response.code < 100:
			request.response.error (506, "%s (Code: 506.%d)" % (response.msg, response.code))		
		else:
			try:	
				self.save_cache (request, handler)					
			except:
				self.wasc.logger.trace ("server")
		
		self.dealloc (request, handler)
		