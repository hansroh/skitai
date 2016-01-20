from . import request_handler as http_request_handler

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; Skitaibot/0.1a)"	

class SSLProxyTunnelHandler (http_request_handler.RequestHandler):
	def __init__ (self, asyncon, request, callback, *args, **karg):
		http_request_handler.RequestHandler.__init__ (self, asyncon, request, callback, "1.1", connection = "keep-alive")
		self.handshaking = False
	
	def get_handshaking_buffer (self):
		req = ("CONNECT %s:%d HTTP/%s\r\nUser-Agent: %s\r\n\r\n" % (
					self.request.address [0], 
					self.request.address [1],
					self.request.http_version, 
					DEFAULT_USER_AGENT
		)).encode ("utf8")
		return req
	
	def start_handshake (self):
		self.handshaking = True
		self.asyncon.push (self.get_handshaking_buffer ())
		self.asyncon.start_request (self)
	
	def finish_handshake (self):	
		if self.response.code == 200:
			self.handshaking = False
			self.response = None
			
			# handsjaking
			self.asyncon.established = True
			self.asyncon.connected = False
			self.asyncon.connecting = True
			# handsjaking ---
			
			for buf in self.get_request_buffer ():
				self.asyncon.push (buf)
														
		else:
			self.response = response.FailedResponse (self.response.code, self.response.msg)
			self.asyncon.close_it = True
			self.asyncon.handle_close ()
							
	def start (self):	
		if not self.asyncon.connected:
			self.start_handshake ()
		else:
			http_request_handler.RequestHandler.start (self)
		
	def found_end_of_body (self):	
		if self.handshaking:
			self.finish_handshake ()								
		else:
			http_request_handler.RequestHandler.found_end_of_body (self)
		
	def handle_disconnected (self):
		return False


