import struct
from skitai.protocol.grpc.producers import grpc_producer

class GRPCRequest (XMLRPCRequest):
	def __init__ (self, uri, method, params = (), headers = None, encoding = "utf8", auth = None, logger = None):
		self.uri = uri
		self.method = method
		self.params = params		
		self.encoding = encoding
		self.auth = (auth and type (auth) is not tuple and tuple (auth.split (":", 1)) or auth)
		self.logger = logger
		self.address, self.path = self.split (uri)
	
		self.headers = {"grpc-timeout": "10S", "grpc-encoding": "gzip"}		
		self.payload = self.serialize ()
		if not self.payload:
			self.method = "GET"		
		else:
			self.headers ["Content-Type"] = "application/grpc+proto"		
	
	def get_cache_key (self):
		return None
		
	def xmlrpc_serialized (self):
		return False
			
	def split (self, uri):
		(host, port), path = XMLRPCRequest.split (self, uri)				
		if path [-1] != "/":
			path += "/"
			self.uri += "/"
		path += self.method
		self.uri += self.method
		return (host, port), path
	
	def serialize (self):
		if type (self.params) is list:
			self.params = iter (self.params)			
		return grpc_producer (self.params)
		
