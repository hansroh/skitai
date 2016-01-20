from . import request_handler
from skitai.protocol.http import tunnel_handler

class SSLProxyTunnelHandler (request_handler.RequestHandler, tunnel_handler.SSLProxyTunnelHandler):
	def start (self):	
		if not self.asyncon.connected:
			self.start_handshake ()						
		else:
			request_handler.RequestHandler.start (self)
		
	def found_end_of_body (self):	
		if self.establishing:
			self.finish_handshake ()											
		else:
			RequestHandler.found_end_of_body (self)
		
