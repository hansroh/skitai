from skitai.client import asynconnect
import time
from M2Crypto import SSL
from skitai.server import https_server
import ssl

class Collector:
	def __init__ (self, asyncon):
		self.asyncon = asyncon
		
	def collect_incoming_data (self, data):
		self.asyncon.push (data)
	
	def abort (self):
		self.asyncon.close_socket ()

		
class Request:
	def __init__ (self, channel):
		self.channel = channel		
	
	def collect_incoming_data (self, data):
		self.channel.push (data)

	def abort (self):
		self.channel.close ()
		

class AsynSSLConnect (asynconnect.AsynSSLConnect):	
	def __init__ (self, proxy_request, logger):
		self.proxy_request = proxy_request		
		
		#convert to https proxy socket
		addr = proxy_request.channel.addr		
		conn = proxy_request.channel.socket
		server = proxy_request.channel.server
		#ssl_ctx = server.ssl_ctx
		ssl_ctx = SSL.Context ("sslv23")
		
		ssl_conn = SSL.Connection (ssl_ctx, conn)
		ssl_conn._setup_ssl (addr)
		ssl_conn.set_connect_state ()
		ssl_conn.connect_ssl ()		
		
		proxy_request.channel.del_channel ()
		proxy_request.channel = https_server.https_channel (server, ssl_conn, addr)
		proxy_request.channel.current_request = proxy_request
					
		self.proxy_request.collector = Collector (self)
		self.proxy_request.channel.set_terminator (None)		
		
		addr, port = proxy_request.uri.split (":")
		port = int (port)
		
		asynconnect.AsynSSLConnect.__init__ (self, (addr, port), logger = logger)
		self.set_terminator (None)
		self.connect ()
		
	def handle_connect (self):
		asynconnect.AsynSSLConnect.handle_connect (self)	
		
		self.request = Request (self.proxy_request.channel)
		self.proxy_request.producer = self.request
		
		self.proxy_request.start (200, "Connection Established")			
		self.proxy_request.done ()
