from skitai.server import http_response
from skitai.lib import producers
import time


class response (http_response.http_response):
	USE_DATA_COMPRESS = True
	
	def __init__ (self, request):
		http_response.http_response.__init__ (self, request)
	
	def push (self, thing):
		if not self.responsable (): return
		if type(thing) is bytes:			
			self.outgoing.push (producers.simple_producer (thing))
		else:
			self.outgoing.push (thing)
			
	def build_reply_header (self):	
		h = [(b":status", str (self.reply_code).encode ("utf8"))]
		for k, v in self.reply_headers:
			h.append ((k.encode ("utf8"), str (v).encode ("utf8")))		
		return h
	
	def hint_promise (self, uri):
		headers = [
			(':path', uri),
			(':authority', self.request.get_header ('host')),	    
	    (':scheme', self.request.scheme),
	    (':method', "GET")	    
	  ]
	   
		additional_headers = [
	   	(k, v) for k, v in [
		   	('accept-encoding', self.request.get_header ('accept-encoding')),
		   	('accept-language', self.request.get_header ('accept-language')),
		    ('cookie', self.request.get_header ('cookie')),
		    ('user-agent', self.request.get_header ('user-agent')),
		    ('referer', "%s://%s%s" % (self.request.scheme, self.request.get_header ('host'), self.request.uri)),	    
		   ] if v
	   ]
	    
		self.request.http2.push_promise (self.request.stream_id, headers, additional_headers)
		
	def done (self, globbing = True, compress = True, force_close = False, next_request = None):
		# removed by HTTP/2.0 Spec.
		self.delete ('transfer-encoding')
		self.delete ('connection')
		
		if len (self.outgoing) == 0:
			outgoing_producer = None
		
		else:
			way_to_compress = ""
			if self.USE_DATA_COMPRESS and not self.has_key ('Content-Encoding'):
				maybe_compress = self.request.get_header ("Accept-Encoding")
				if maybe_compress and self.has_key ("content-length") and int (self ["Content-Length"]) <= http_response.UNCOMPRESS_MAX:
					maybe_compress = ""
				else:	
					content_type = self ["Content-Type"]
					if maybe_compress and content_type and (content_type.startswith ("text/") or content_type.endswith ("/json-rpc")):
						accept_encoding = [x.strip () for x in maybe_compress.split (",")]
						if "gzip" in accept_encoding:
							way_to_compress = "gzip"
						elif "deflate" in accept_encoding:
							way_to_compress = "deflate"
			
				if way_to_compress:
					if self.has_key ('Content-Length'):
						self.delete ("content-length") # rebuild
					self.update ('Content-Encoding', way_to_compress)
			
			if way_to_compress:
				if way_to_compress == "gzip":
					producer = producers.gzipped_producer
				else: # deflate
					producer = producers.compressed_producer
				outgoing_producer = producer (producers.composite_producer (self.outgoing))						
			else:
				outgoing_producer = producers.composite_producer (self.outgoing)			
			outgoing_producer = producers.globbing_producer (producers.hooked_producer (outgoing_producer, self.log))
		
		try:
			self.request.http2.push_response (
				self.request.stream_id, 
				self.build_reply_header (),
				outgoing_producer
			)
			
		except:
			self.request.logger.trace ()			
			self.request.http2.close (True)		
		else:
			if next_request: # like ssl tunnel
				request, terminator = next_request
				self.request.channel.current_request = request
				self.request.channel.set_terminator (terminator)
	
	def log (self, bytes):		
		self.request.channel.server.log_request (
			'%s:%d %s%s %s %d %dms %dms'
			% (self.request.channel.addr[0],
			self.request.channel.addr[1],			
			self.request.is_promise and "PUSH-" or "",
			self.request.request,
			self.reply_code,			
			bytes,
			self.htime,
			(time.time () - self.stime) * 1000
			)
		)

		
