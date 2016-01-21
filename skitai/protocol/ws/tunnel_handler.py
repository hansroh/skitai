from . import request_handler
from skitai.protocol.http import tunnel_handler

class ProxyTunnelHandler (request_handler.RequestHandler, tunnel_handler.ProxyTunnelHandler):
	def start (self):	
		if self.asyncon.established:			
			request_handler.RequestHandler.start (self)			
		else:
			tunnel_handler.ProxyTunnelHandler.start (self)
	
	def get_request_buffer (self):		
		if self.asyncon.established:				
			return request_handler.RequestHandler.get_request_buffer (self)			
		else:
			return tunnel_handler.ProxyTunnelHandler.get_request_buffer (self)
		
	def collect_incoming_data (self, data):		
		if self.asyncon.established:
			request_handler.RequestHandler.collect_incoming_data (self, data)	
		else:
			tunnel_handler.ProxyTunnelHandler.collect_incoming_data (self, data)
	
	def found_terminator (self):		
		if self.asyncon.established:
			request_handler.RequestHandler.found_terminator (self)			
		else:
			tunnel_handler.ProxyTunnelHandler.found_terminator (self)			
		
	def found_end_of_body (self):	
		if self.asyncon.established:
			request_handler.RequestHandler.found_end_of_body (self)			
		else:
			tunnel_handler.ProxyTunnelHandler.found_end_of_body (self)
			if self.asyncon.established:
				self._handshaking = True
						

class SSLProxyTunnelHandler (ProxyTunnelHandler, tunnel_handler.ProxyTunnelHandler):
	def convert_to_ssl (self):
		tunnel_handler.ProxyTunnelHandler.convert_to_ssl (self)
