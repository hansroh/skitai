import http_date, producers, utility
import compressors, zlib
import time

class http_response:
	reply_code = 200
	reply_message = ""
	is_sent_response = False
		
	def __init__ (self, request):
		self.request = request
		self.reply_headers = [
			('Server', "sae"),
			('Date', http_date.build_http_date (time.time()))
		]
		self.outgoing = producers.fifo ()
		
	def __setitem__ (self, key, value):
		self.set (key, value)

	def __getitem__ (self, key):
		return self.get (key)
	
	def __delitem__ (self, k):
		self.delete (k)
	
	def has_key (self, key):
		key = key.lower ()
		return key in map (lambda x: x [0].lower (), self.reply_headers)		
			
	def set (self, key, value):
		self.reply_headers.append ((key, value))
			
	def get (self, key):
		key = key.lower ()
		for k, v in self.reply_headers:
			if k.lower () == key:
				return v
		
	def delete (self, key):
		index = 0
		found = 0
		key = key.lower ()
		for hk, hv in self.reply_headers:
			if key == hk.lower ():
				found = 1
				break
			index += 1
		
		if found:
			del self.reply_headers [index]
			self.delete (key)
		
	def update (self, key, value):
		self.delete (key)
		self.set (key, value)
	
	def build_reply_header (self):		
		return '\r\n'.join (
			[self.response(self.reply_code, self.reply_message)] + map (
				lambda x: '%s: %s' % x,
				self.reply_headers
				)
			) + '\r\n\r\n'
	
	def response (self, code, msg):
		if not msg:
			try:
				msg = self.responses [code]
			except KeyError: 
				msg = "Undefined"	
		return 'HTTP/%s %d %s' % (self.request.version, code, msg)
		
	def start (self, code, msg = "", headers = None):
		self.reply_code = code
		if not msg:
			self.reply_message = self.responses [code]
		else:	
			self.reply_message = msg
			
		if headers:
			for k, v in headers:
				self.set (k, v)
	
	def reply (self, code, msg = "", headers = None):
		self.start (code, msg, headers)
	
	def instant (self, code):
		if self.request.version != "1.1": return		
		message = self.responses [code]
		self.request.channel.push (self.response (code, message) + "\r\n\r\n")
	
	def abort (self, code, why = ""):
		self.request.channel.reject ()		
		self.error (code, why, force_close = True)
		
	def error (self, code, why = "", force_close = False):
		self.reply_code = code
		message = self.responses [code]
		if not why:
			why = message

		s = self.DEFAULT_ERROR_MESSAGE % {
			'code': code,
			'message': message,
			'info': why
		}
		
		self.update ('Content-Length', len(s))
		self.update ('Content-Type', 'text/html')
		self.delete ('content-encoding')
		self.delete ('expires')
		self.delete ('cache-control')
		self.delete ('set-cookie')

		self.push (s)
		self.done (True, True, force_close)
	
	def push (self, thing):
		if self.request.channel is None: return		
		if type(thing) == type(''):
			self.outgoing.push (producers.simple_producer (thing))
		else:
			self.outgoing.push (thing)
				
	def done (self, globbing = True, compress = True, force_close = False):
		if self.request.channel is None: return
		if self.is_sent_response:
			return
		self.is_sent_response = True
				
		connection = utility.get_header (utility.CONNECTION, self.request.header).lower()
		close_it = False
		way_to_compress = ""
		wrap_in_chunking = False
		
		if force_close:
			close_it = True
		
		else:
			if self.request.version == '1.0':
				if connection == 'keep-alive':
					if not self.has_key ('Content-Length'):
						close_it = True
				else:
					close_it = True
			
			elif self.request.version == '1.1':
				if connection == 'close':
					close_it = True
				elif not self.has_key ('Content-Length'):
					wrap_in_chunking = True
					
			elif self.request.version is None:
				close_it = True
		
		if close_it:
			self.update ('Connection', 'close')
		else:
			self.update ('Connection', 'keep-alive')
			
		if compress and not self.has_key ('Content-Encoding'):
			maybe_compress = self.request.get_header ("Accept-Encoding")
			if maybe_compress and self.has_key ("Content-Length") and self ["Content-Length"] < 1024:
				maybe_compress = ""
			
			else:	
				content_type = self ["Content-Type"]
				if maybe_compress and content_type and (content_type.startswith ("text/") or content_type.endswith ("/json-rpc")):
					accept_encoding = map (lambda x: x.strip (), maybe_compress.split (","))
					if "gzip" in accept_encoding:
						way_to_compress = "gzip"
					elif "deflate" in accept_encoding:
						way_to_compress = "deflate"
		
			if way_to_compress:
				if self.has_key ('Content-Length'):
					self.delete ("Content-Length") # rebuild
					wrap_in_chunking = True
				self.update ('Content-Encoding', way_to_compress)
		
		if wrap_in_chunking:
			self.delete ('Content-Length')
			self.update ('Transfer-Encoding', 'chunked')
			
			if way_to_compress:
				if way_to_compress == "gzip": 
					producer = producers.gzipped_producer
				else: # deflate
					producer = producers.compressed_producer
				outgoing_producer = producer (producers.composite_producer (self.outgoing))
				
			else:
				outgoing_producer = producers.composite_producer (self.outgoing)				
				
			outgoing_producer = producers.chunked_producer (outgoing_producer)
			outgoing_header = producers.simple_producer (self.build_reply_header())
			outgoing_producer = producers.composite_producer (
				producers.fifo([outgoing_header, outgoing_producer])
			)
			
		else:
			self.delete ('Transfer-Encoding')
			
			if way_to_compress:
				if way_to_compress == "gzip":
					compressor = compressors.GZipCompressor ()
				else: # deflate
					compressor = zlib.compressobj (6, zlib.DEFLATED)
				
				cdata = ""
				has_producer = 1
				while 1:
					has_producer, producer = self.outgoing.pop ()
					if not has_producer: break
					cdata += compressor.compress (producer.data)				
				cdata += compressor.flush ()
				
				self.update ("Content-Length", len (cdata))
				self.outgoing = producers.fifo ([producers.simple_producer (cdata)])
			
			outgoing_header = producers.simple_producer (self.build_reply_header())
			self.outgoing.push_front (outgoing_header)
			outgoing_producer = producers.composite_producer (self.outgoing)
		
		try:
			if globbing:				
				self.request.channel.push_with_producer (producers.globbing_producer (producers.hooked_producer (outgoing_producer, self.log)))
			else:
				self.request.channel.push_with_producer (producers.hooked_producer (outgoing_producer, self.log))
			
			self.request.channel.current_request = None
			# proxy collector and producer is related to asynconnect
			# and relay data with channel
			# then if request is suddenly stopped, make sure close them
			self.request.channel.abort_when_close ([self.request.collector, self.request.producer])
			if close_it:
				self.request.channel.close_when_done()
		
		except:
			self.request.logger.trace ()
			self.request.logger.log (
				'channel maybe closed',
				'warning'
			)		
	
	def log (self, bytes):		
		self.request.channel.server.log_request (
			'%s:%d %s %s %s %d'
			% (self.request.channel.addr[0],
			self.request.channel.addr[1],			
			self.request.request,
			self.request.requeststr,
			self.reply_code,			
			bytes)
			)
	
		
	# Default error message
	DEFAULT_ERROR_MESSAGE = '\r\n'.join (
		[
		 '<!DOCTYPE html>',
		 '<html>',
		 '<head>',
		 '<title>%(code)d %(message)s</title>',
		 '<style>',
		 'body, p {font-family: "arial"; font-size: 12px;}',
		 'h1 {font-family: "arial black"; font-weight: bold; font-size: 24px;}',		 
		 '</style>',
		 '</head>',
		 '<body>',
		 '<h1>%(code)d %(message)s</h1>',
		 '<p>Error code %(code)d.',
		 '<br>Message: %(message)s.',		 
		 '<p><strong>%(info)s</strong>',
		 '</body>',
		 '</html>',
		 ''
		 ]
	)
	
	responses = {
		100: "Continue",
		101: "Switching Protocols",
		200: "OK",
		201: "Created",
		202: "Accepted",
		203: "Non-Authoritative Information",
		204: "No Content",
		205: "Reset Content",
		206: "Partial Content",
		300: "Multiple Choices",
		301: "Moved Permanently",
		302: "Moved Temporarily",
		303: "See Other",
		304: "Not Modified",
		305: "Use Proxy",
		400: "Bad Request",
		401: "Unauthorized",
		402: "Payment Required",
		403: "Forbidden",
		404: "Not Found",
		405: "Method Not Allowed",
		406: "Not Acceptable",
		407: "Proxy Authentication Required",
		408: "Request Time-out",
		409: "Conflict",
		410: "Gone",
		411: "Length Required",
		412: "Precondition Failed",
		413: "Request Entity Too Large",
		414: "Request-URI Too Large",
		415: "Unsupported Media Type",
		500: "Internal Server Error",
		501: "Not Implemented",
		502: "Bad Gateway",
		503: "Service Unavailable",
		504: "Gateway Time-out",
		505: "HTTP Version not supported",
		506: "Proxy Error"
	}		
		