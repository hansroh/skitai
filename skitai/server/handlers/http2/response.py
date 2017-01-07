from skitai.server import http_response
from skitai.lib import producers
import time
	

class response (http_response.http_response):	
	def __init__ (self, request):
		http_response.http_response.__init__ (self, request)
	
	def set_streaming (self):
		self._is_streaming = True
		
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
		
	def done (self):
		self.htime = (time.time () - self.stime) * 1000
		self.stime = time.time () #for delivery time
		
		if not self.responsable (): return
		self.is_done = True
		if self.request.channel is None: return
		
		# removed by HTTP/2.0 Spec.
		self.delete ('transfer-encoding')
		self.delete ('connection')
		
		if len (self.outgoing) == 0:
			outgoing_producer = None
		else:
			outgoing_producer = producers.composite_producer (self.outgoing)
		
		if not self.is_streaming () and not self.has_key ('Content-Encoding'):
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
					producer = producers.gzipped_producer
				else: # deflate
					producer = producers.compressed_producer		
				outgoing_producer = producer (outgoing_producer)
					
		if not self.is_streaming ():
			outgoing_producer = producers.globbing_producer (producers.hooked_producer (outgoing_producer, self.log))				
		else:
			outgoing_producer = producers.hooked_producer (outgoing_producer, self.log)
		
		try:
			self.request.http2.handle_response (
				self.request.stream_id, 
				self.build_reply_header (),
				outgoing_producer,
				streaming = self.is_streaming ()
			)
			
		except:
			self.request.logger.trace ()			
			self.request.http2.close (True)
		
		