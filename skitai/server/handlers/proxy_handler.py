from . import wsgi_handler, collectors
import re
import skitai
from skitai.protocol.http import request as http_request
from skitai.protocol.http import request_handler as http_request_handler
from skitai.protocol.http import response as http_response
from skitai.lib import compressors
from skitai.lib import producers
import time

post_max_size = wsgi_handler.Handler.post_max_size
upload_max_size = wsgi_handler.Handler.upload_max_size
PROXY_TUNNEL_KEEP_ALIVE = 120

class AsynTunnel:
	collector = None
	producer = None
	def __init__ (self, asyncon, handler):
		self.asyncon = asyncon
		self.handler = handler
		self.bytes = 0
		self.asyncon.set_terminator (None)
		
	def collect_incoming_data (self, data):
		#print (">>>>>>>>>>>>", data)
		self.bytes += len (data)		
		self.asyncon.push (data)
	
	def close (self):
		# will be closed by channel
		#print (">>>>>>>>>>>>> AsynTunnel xlosed", self.handler.request.uri)
		self.handler.channel_closed ()
		
	
class TunnelHandler:
	keep_alive = 120			
	def __init__ (self, asyncon, request, channel):		
		self.asyncon = asyncon		
		self.request = request
		self.channel = channel
		
		self.asyntunnel = AsynTunnel (asyncon, self)		
		self.channel.set_response_timeout	(PROXY_TUNNEL_KEEP_ALIVE)
		self.asyncon.set_network_delay_timeout (PROXY_TUNNEL_KEEP_ALIVE)
		self.channel.add_closing_partner (self.asyntunnel)
		
		self.bytes = 0
		self.stime = time.time ()
				
	def trace (self, name = None):
		if name is None:
			name = "tunnel://%s:%d" % self.asyncon.address
		self.channel.trace (name)
		
	def log (self, message, type = "info"):
		uri = "tunnel://%s:%d" % self.asyncon.address
		self.channel.log ("%s - %s" % (uri, message), type)
					
	def collect_incoming_data (self, data):	
		#print ("<<<<<<<<<<<<", data[:20])
		self.bytes += len (data)
		self.channel.push (data)
		
	def log_request (self):
		htime = (time.time () - self.stime) * 1000
		self.channel.server.log_request (
			'%s:%d CONNECT tunnel://%s:%d HTTP/1.1 200 %d/%d %dms %dms'
			% (self.channel.addr[0],
			self.channel.addr[1],			
			self.asyncon.address [0],
			self.asyncon.address [1],
			self.asyntunnel is not None and self.asyntunnel.bytes or 0,
			self.bytes,
			htime,
			htime
			)
		)
		
	def connection_closed (self, why, msg):
		#print ("------------Asyncon_disconnected", self.request.uri, self.bytes)
		# Disconnected by server mostly caused by Connection: close header				
		self.channel.close_when_done ()
		self.channel.current_request = None
		
	def channel_closed (self):
		#print ("------------channel_closed", self.request.uri, self.bytes)
		self.asyncon.handler = None
		self.asyncon.disconnect ()
		self.asyncon.end_tran ()


class ProxyRequestHandler (http_request_handler.RequestHandler):
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
	
	ESTABLISHED = b"HTTP/1.1 200 Connection Established\r\nServer: " + skitai.NAME.encode ("utf8")
	def has_been_connected (self):
		if self.request.method == "connect":
			self.buffer =	self.ESTABLISHED
			self.found_terminator ()
	
	def will_open_tunneling (self):
		return self.response.code == 200 and self.response.msg.lower () == "connection established"
	
	def connection_closed (self, why, msg):
		if self.client_request.channel is None: return
		return http_request_handler.RequestHandler.connection_closed (self, why, msg)
					
	def close_case (self):
		# unbind readable/writable methods
		if self.asyncon:
			self.asyncon.ready = None
			self.asyncon.affluent = None
			if self.client_request.channel:
				self.client_request.channel.ready = None
				self.client_request.channel.affluent = None
			else:
				return
			self.asyncon.handler = self.new_handler
			
		if self.callback:
			self.callback (self)
	
	def found_end_of_body (self):
		# proxy should not handle authorization		
		if self.will_be_close ():
			self.asyncon.disconnect ()
		self.close_case_with_end_tran ()
	
	def create_tunnel (self):
		self.asyncon.established = True		
		self.new_handler = TunnelHandler (self.asyncon, self.request, self.client_request.channel)
		# next_request = (new request, new terminator)
		self.client_request.response.done (globbing = False, compress = False, next_request = (self.new_handler.asyntunnel, None)) 
			
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

	
class ProxyResponse (http_response.Response):
	SIZE_LIMIT = 2**24
	
	def __init__ (self, request, header, accept_gzip, client_request, asyncon):		
		self.client_request = client_request
		self.asyncon = asyncon
		self.accept_gzip = accept_gzip		
		self.request = request
		self.header_s = header		
		if header [:2] == "\r\n":
			header = header [2:]
		header = header.split ("\r\n")		
		self.response = header [0]
		self.header = header [1:]
		self._header_cache = {}
		self.flushed_time = 0
		self.client_request.producer = self
		self.version, self.code, self.msg = http_response.crack_response (self.response)
		self.p, self.u = None, None
		self.decompressor = None
		self.gzip_compressed = False	
		self.make_decompressor = False
		
		content_encoding = self.get_header ("Content-Encoding")			
		if content_encoding == "gzip":
			if self.accept_gzip:
				self.gzip_compressed = True
			else:	
				self.make_decompressor = True
						
		self.size = 0
		self.got_all_data = False
		
		self.reqtype = "HTTP"				
		if self.client_request.get_header ("cookie"):
			self.max_age = 0
		else:	
			self.set_max_age ()
	
	def body_expected (self):
		cl = self.get_header ("Content-Length")
		if cl == 0:
			self.got_all_data = True
			return False
		
		te = self.get_header ("Transfer-Encoding")
		if cl is None and te != "chunked":
			hv = self.version
			cn = self.get_header ("Connection")			
			if cn is None:
				if hv == "1.0": cn = "close"
				else: cn = "keep-alive"	
			else:
				cn = cn.lower ()			
			if cn == "keep-alive":				
				self.got_all_data = True
				return False
		
		if self.p is None:
			self.p, self.u = http_response.getfakeparser (cache = self.max_age)
			if self.make_decompressor:
				self.decompressor = compressors.GZipDecompressor ()
			
		return True
		
	def init_buffer (self):
		# do this job will be executed in body_expected ()
		pass
		
	def is_gzip_compressed (self):
		return self.gzip_compressed
	
	def close (self):
		self.client_request.producer = None
		try: self.u.data = []
		except AttributeError: pass		
		self.asyncon.disconnect ()
		self.asyncon.end_tran ()
			
	def affluent (self):
		# if channel doesn't consume data, delay recv data
		return len (self.u.data) < 1000
		
	def ready (self):
		# if exist consumable data or wait		
		return len (self.u.data) or self.got_all_data
		
	def more (self):
		self.flushed_time = time.time ()
		return self.u.read ()


class Collector (collectors.FormCollector):
	# same as asyncon ac_in_buffer_size
	ac_in_buffer_size = 4096
	asyncon = None
	def __init__ (self, handler, request):
		self.handler = handler
		self.request = request
		self.data = []
		self.cache = []
		self.cached = False
		self.got_all_data = False
		self.length = 0 
		self.content_length = self.get_content_length ()
	
	def reuse_cache (self):
		self.data = self.cache + self.data		
		self.cache = []
			
	def start_collect (self):	
		if self.content_length == 0:
			return self.found_terminator ()
			
		if self.content_length <= post_max_size: #5M
			self.cached = True
		
		self.request.channel.set_terminator (self.content_length)
	
	def close (self):
		# channel disconnected
		self.data = []
		self.cache = []
		self.request.collector = None
		
		# abort immediatly
		if self.asyncon:
			self.asyncon.ready = None
			self.asyncon.affluent = None
			self.asyncon.handler = None
			self.asyncon.close ()
				
	def collect_incoming_data (self, data):
		#print "proxy_handler.collector << %d" % len (data), id (self)
		self.length += len (data)
		self.data.append (data)

	def found_terminator (self):
		self.request.channel.set_terminator (b'\r\n\r\n')
		self.got_all_data = True
		self.request.collector = None
		# don't request.collector = None => do it at callback ()
		# because this collector will be used in Request.continue_start() later
	
	def get_cache (self):
		return b"".join (self.cache)
	
	def affluent (self):
		# if channel doesn't consume data, delay recv data		
		return len (self.data) < 1000
		
	def ready (self):
		return len (self.data) or self.got_all_data
	
	def more (self):
		if not self.data:
			return b""
						
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
		return b"".join (data)
		
			
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
			current_post_max_size = ct.startswith ("multipart/form-data") and upload_max_size or post_max_size
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
		if response.code >= 700:
			request.response.error (506, response.msg)
		
		else:
			try:
				self.save_cache (request, handler)					
			except:
				self.wasc.logger.trace ("server")
		
		self.dealloc (request, handler)
		