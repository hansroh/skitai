from . import wsgi_handler
import skitai
from skitai.protocol.http import request as http_request
from skitai.protocol.http import request_handler as http_request_handler
from .proxy import POST_MAX_SIZE, UPLOAD_MAX_SIZE
from .proxy.collector import Collector
from .proxy.tunnel import TunnelHandler
from .proxy.response import ProxyResponse


class proxy_request_handler (http_request_handler.RequestHandler):
	def __init__ (self, asyncon, request, callback, client_request, collector, connection = "keep-alive"):
		http_request_handler.RequestHandler.__init__ (self, asyncon, request, callback, "1.1", connection)
		self.collector = collector
		self.client_request = client_request
		self.is_tunnel = False
		self.new_handler = None
			
	def add_reply_headers (self):		
		for line in self.response.get_headers ():			
			try: k, v = line.split (": ", 1)
			except:	continue			
			ll = k.lower ()
			if ll in ("expires", "date", "connection", "keep-alive", "content-length", "transfer-encoding", "content-encoding", "age", "vary"):
				continue
			if ll == "server":
				self.client_request.response.update ("Server", v.strip () + ", " + skitai.NAME)
				continue
			self.client_request.response [k] = v.strip ()			
	
	ESTABLISHED = b" 200 Connection Established\r\nServer: " + skitai.NAME.encode ("utf8")
	def has_been_connected (self):
		if self.request.method == "connect":
			self.buffer =	b"HTTP/" + self.client_request.version.encode ("utf8") + self.ESTABLISHED			
			self.found_terminator ()
	
	def will_open_tunneling (self):
		return self.response.code == 200 and self.response.msg.lower () == "connection established"
	
	def connection_closed (self, why, msg):
		if self.client_request.channel is None:
			return self.close_case_with_end_tran ()			
		return http_request_handler.RequestHandler.connection_closed (self, why, msg)
					
	def close_case (self):
		# unbind readable/writable methods
		if self.asyncon:
			self.asyncon.ready = None
			self.asyncon.affluent = None			
			if self.client_request.channel:
				self.client_request.channel.ready = None
				self.client_request.channel.affluent = None			
			
			self.asyncon.handler = self.new_handler			
		
		if self.callback:			
			self.callback (self)
	
	def found_end_of_body (self):		
		if self.response:
			self.response.done ()
		if self.will_be_close ():
			self.asyncon.disconnect ()
		self.close_case_with_end_tran ()
	
	def create_tunnel (self):
		self.asyncon.established = True		
		self.new_handler = TunnelHandler (self.asyncon, self.request, self.client_request.channel)
		self.client_request.response.done (False, False, False, (self.new_handler.asyntunnel, None)) 
			
	def create_response (self):		
		if not self.client_request.channel: return

		buffer, self.buffer = self.buffer, b""
		accept_gzip = ""
		accept_encoding = self.client_request.get_header ("Accept-Encoding")
		if accept_encoding and accept_encoding.find ("gzip") != -1:
			accept_gzip = "gzip"
		
		try:
			self.response = ProxyResponse (self.request, buffer.decode ("utf8"), accept_gzip, self.client_request, self.asyncon)
		except:
			#print (buffer)
			self.log ("response header error: `%s`" % repr (buffer [:80]), "error")
			self.asyncon.handle_close (708, "Response Header Error")
			return

		if self.is_continue_response ():
			# maybe response code is 100 continue
			return
		
		if self.will_open_tunneling ():
			self.create_tunnel ()
			self.close_case ()
			return
				
		self.client_request.response.start (self.response.code, self.response.msg)
		self.add_reply_headers ()
		
		if self.response.is_gzip_compressed ():
			self.client_request.response ["Content-Encoding"] = "gzip"
		
		if self.response.body_expected ():
			self.client_request.response.push (self.response)
			#self.client_request.channel.add_closable_producer (self.response)
			# in relay mode, possibly delayed
			self.client_request.channel.ready = self.response.ready			
			self.asyncon.affluent = self.response.affluent
		
		self.client_request.response.done (globbing = False, compress = False)
	
	def start (self):
		if not self.client_request.channel: return
		
		self.buffer, self.response = b"", None
		self.asyncon.set_terminator (b"\r\n\r\n")	
		
		if self.request.method != "connect":
			for buf in self.get_request_buffer ():
				self.asyncon.push (buf)
			if self.collector:
				self.collector.reuse_cache ()
				if not self.collector.got_all_data:
					self.asyncon.ready = self.collector.ready
					self.client_request.channel.affluent = self.collector.affluent
					# don't init_send cause of producer has no data yet
				self.asyncon.push_with_producer (self.collector, init_send = False)
				
		self.asyncon.begin_tran (self)
								
	def get_request_buffer (self):
		hc = {}
		address = self.request.get_address ()
		if address [1] in (80, 443):
			hc ["Host"] = "%s" % address [0]
		else:
			hc ["Host"] = "%s:%d" % address
			
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
		hc ["X-Proxy-Agent"] = skitai.NAME
				
		req = "%s %s HTTP/%s\r\n%s\r\n\r\n" % (
			method,
			self.request.path,
			self.http_version,
			"\r\n".join (["%s: %s" % x for x in list(hc.items ())])			
		)
		
		#print ("####### SKITAI => SERVER ##########################")
		#print (req)
		#print ("---------------------------------")
		return [req.encode ("utf8")]

			
class Handler (wsgi_handler.Handler):
	def __init__ (self, wasc, clusters, cachefs = None, unsecure_https = False):
		self.wasc = wasc
		self.clusters = clusters
		self.cachefs = cachefs
		self.unsecure_https = unsecure_https
		self.q = {}
				
	def match (self, request):
		uri = request.uri.lower ()
		if uri.startswith ("http://") or uri.startswith ("ws://") or uri.startswith ("wss://"):
			return 1
		if self.unsecure_https and uri.startswith ("https://"):
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
		if self.has_valid_cache (request, collector is not None):
			return
		
		try:
			if asyncon is None:		
				if request.command == "connect":
					asyncon_key = "tunnel://" + request.uri + "/"
				else:
					asyncon_key = request.uri					
				asyncon = self.clusters ["__socketpool__"].get (asyncon_key)
					
			req = http_request.HTTPRequest (request.uri, request.command, collector is not None, logger = self.wasc.logger.get ("server"))				
			r = proxy_request_handler (asyncon, req, self.callback, request, collector)			
			if collector:
				collector.asyncon = asyncon
			r.start ()
						
		except:
			self.wasc.logger.trace ("server")			
			request.response.error (500, "", "Proxy request has been failed.")
		
	def has_valid_cache (self, request, has_data):
		if not self.cachefs:
			request.response ["X-Skitaid-Cache-Lookup"] = "NOCACHE"
			return False
		
		if has_data:
			# have collector, cna't cache
			request.response ["X-Skitaid-Cache-Lookup"] = "PASSED"
			return False
				
		cachable = self.cachefs.is_cachable (
			request.get_header ("cache-control"),
			request.get_header ("cookie") is not None, 
			request.get_header ("authorization") is not None, 
			request.get_header ("pragma")			
		)		
		if not cachable:
			request.response ["X-Skitaid-Cache-Lookup"] = "PASSED"
			return False
		
		try:
			accept_encoding = request.get_header ("accept-encoding")
			hit, compressed, max_age, content_type, content = self.cachefs.get (request.uri, None, accept_encoding and accept_encoding.find ("gzip") != -1)
					
		except:
			self.wasc.logger.trace ("server")	
			return False
		
		else:
			if hit is None:
				request.response ["X-Skitaid-Cache-Lookup"] = "MISS"
				return False
				
		if hit == -1:
			request.response ["X-Skitaid-Cache-Lookup"] = "MEM_HIT"
		else:
			request.response ["X-Skitaid-Cache-Lookup"] = "HIT"
		if content_type:
			request.response ["Content-Type"] = content_type					
		request.response ["Cache-Control"] = "max-age=%d" % max_age
		if compressed:
			request.response ["Content-Encoding"] = "gzip"
		request.response.push (content)
		request.response.done ()
		return True
	
	def save_cache (self, request, handler):
		try:			
			if self.cachefs and not handler.request.data and handler.response.max_age:
				self.cachefs.save (
					request.uri, None, 
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
		