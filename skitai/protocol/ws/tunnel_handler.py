from . import request_handler
from skitai.protocol.http import tunnel_handler


class ProxyTunnelHandler (request_handler.RequestHandler, tunnel_handler.ProxyTunnelHandler):
	def start (self):	
		if not self.asyncon.established:			
			tunnel_handler.ProxyTunnelHandler.start_handshake (self)						
		else:
			request_handler.RequestHandler.start (self)
		
	def collect_incoming_data (self, data):
		print ("++++++++++++", self.asyncon.established, self.asyncon.get_terminator ())
		print (`data`)
		if not self.asyncon.established:
			tunnel_handler.ProxyTunnelHandler.collect_incoming_data (self, data)
		else:
			request_handler.RequestHandler.collect_incoming_data (self, data)	
	
	def found_terminator (self):
		print ("------------", self.asyncon.established)
		if not self.asyncon.established:
			tunnel_handler.ProxyTunnelHandler.found_terminator (self)			
		else:
			request_handler.RequestHandler.found_terminator (self)
					
	def found_end_of_body (self):	
		print (">>>>>>>>>>", self.asyncon.established, self.response.code)
		if not self.asyncon.established:
			tunnel_handler.ProxyTunnelHandler.found_end_of_body (self)
			if self.asyncon.established:
				request_handler.RequestHandler.start (self)
		else:
			request_handler.RequestHandler.found_end_of_body (self)


class SSLProxyTunnelHandler (ProxyTunnelHandler, tunnel_handler.ProxyTunnelHandler):
	def convert_to_ssl (self):
		tunnel_handler.ProxyTunnelHandler.convert_to_ssl (self)
