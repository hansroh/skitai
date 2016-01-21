from . import request_handler as http_request_handler
from skitai.protocol.http import response

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; Skitaibot/0.1a)"	

class ProxyTunnelHandler (http_request_handler.RequestHandler):
	def __init__ (self, asyncon, request, callback, *args, **karg):
		http_request_handler.RequestHandler.__init__ (self, asyncon, request, callback, "1.1", connection = "keep-alive")
	
	def get_handshaking_buffer (self):
		req = ("CONNECT %s:%d HTTP/%s\r\nUser-Agent: %s\r\n\r\n" % (
					self.request.address [0], 
					self.request.address [1],
					self.http_version, 
					DEFAULT_USER_AGENT
		)).encode ("utf8")
		return req
	
	def start_handshake (self):
		self.asyncon.push (self.get_handshaking_buffer ())
		self.asyncon.start_request (self)		
	
	def convert_to_ssl (self):
		pass
		
	def finish_handshake (self):
		if self.response.code == 200:
			self.asyncon.established = True
			self.response = None
			self.convert_to_ssl ()
			for buf in self.get_request_buffer ():
				self.asyncon.push (buf)														
		else:
			self.response = response.FailedResponse (self.response.code, self.response.msg)
			self.asyncon.close_it = True
			self.asyncon.handle_close ()
							
	def start (self):	
		if not self.asyncon.established:
			self.start_handshake ()
		else:
			http_request_handler.RequestHandler.start (self)
		
	def found_end_of_body (self):	
		if not self.asyncon.established:
			self.finish_handshake ()											
		else:
			http_request_handler.RequestHandler.found_end_of_body (self)
		
	def handle_disconnected (self):
		return False


class SSLProxyTunnelHandler (ProxyTunnelHandler):
	def convert_to_ssl (self):
		self.asyncon.established = True
		self.asyncon.connected = False
		self.asyncon.connecting = True

