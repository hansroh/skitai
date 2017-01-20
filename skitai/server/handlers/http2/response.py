from skitai.server import http_response
from aquests.lib import producers
from h2.errors import CANCEL, PROTOCOL_ERROR, FLOW_CONTROL_ERROR, NO_ERROR
import time
	

class response (http_response.http_response):	
	def __init__ (self, request):
		http_response.http_response.__init__ (self, request)
	
	def set_streaming (self):
		self._is_async_streaming = True
		
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
		
	def done (self, force_close = False, upgrade_to = None):
		if not self.is_responsable (): return
		self._is_done = True
		if self.request.http2 is None: return
		
		self.htime = (time.time () - self.stime) * 1000
		self.stime = time.time () #for delivery time
		
		# removed by HTTP/2.0 Spec.
		self.delete ('transfer-encoding')
		self.delete ('connection')
		
		# compress payload and globbing production
		do_optimize = True
		if upgrade_to or self.is_async_streaming ():
			do_optimize = False
		
		if not self.outgoing:
			self.delete ('content-type')
			self.delete ('content-length')
			outgoing_producer = None
			
		elif len (self.outgoing) == 1 and hasattr (self.outgoing.first (), "ready"):
			outgoing_producer = producers.composite_producer (self.outgoing)
			do_optimize = False
		
		else:
			outgoing_producer = producers.composite_producer (self.outgoing)			
			if do_optimize and not self.has_key ('Content-Encoding'):
				way_to_compress = ""			
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
					if way_to_compress == "gzip":
						compressing_producer = producers.gzipped_producer
					else: # deflate
						compressing_producer = producers.compressed_producer		
					outgoing_producer = compressing_producer (outgoing_producer)
		
		if outgoing_producer:
			outgoing_producer = producers.hooked_producer (outgoing_producer, self.log)
			if do_optimize:
				outgoing_producer = producers.globbing_producer (outgoing_producer)				

		if self.request.http2 is None: return
		if upgrade_to:
			# do not change http2 channel
			request, terminator = upgrade_to
			self.request.channel.current_request = request
			self.request.channel.set_terminator (terminator)
		
		logger = self.request.logger #IMP: for  disconnect with request		
		try:
			self.request.http2.handle_response (
				self.request.stream_id, 
				self.build_reply_header (),
				outgoing_producer,
				force_close = force_close
			)
			
		except:
			logger.trace ()			
		