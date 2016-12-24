from skitai.protocol.http import response as http_response
from skitai.lib import compressors
import time


class ProxyResponse (http_response.Response):
	SIZE_LIMIT = 2**24
	
	def __init__ (self, request, header, accept_gzip, client_request, asyncon):		
		self.client_request = client_request
		self.asyncon = asyncon
		self.accept_gzip = accept_gzip		
		self.request = request
		self.header_s = header		
		if header [:2] == "\r\n":
			header = header [2:]
		header = header.split ("\r\n")		
		self.response = header [0]
		self.header = header [1:]
		self._header_cache = {}
		self.flushed_time = 0
		self.client_request.producer = self
		self.version, self.code, self.msg = http_response.crack_response (self.response)
		self.p, self.u = None, None
		self.decompressor = None
		self.gzip_compressed = False	
		self.is_xmlrpc_return = False
		self.make_decompressor = False
		
		content_encoding = self.get_header ("Content-Encoding")			
		if content_encoding == "gzip":
			if self.accept_gzip:
				self.gzip_compressed = True
			else:	
				self.make_decompressor = True
						
		self.size = 0
		self.got_all_data = False
		self.set_max_age ()
	
	def body_expected (self):
		cl = self.get_header ("Content-Length")
		if cl == 0:
			self.got_all_data = True
			return False
		
		te = self.get_header ("Transfer-Encoding")
		if cl is None and te != "chunked":
			hv = self.version
			cn = self.get_header ("Connection")			
			if cn is None:
				if hv == "1.0": cn = "close"
				else: cn = "keep-alive"	
			else:
				cn = cn.lower ()			
			if cn == "keep-alive":				
				self.got_all_data = True
				return False
		
		if self.p is None:
			self.p, self.u = http_response.getfakeparser (cache = self.max_age)
			if self.make_decompressor:
				self.decompressor = compressors.GZipDecompressor ()
			
		return True
		
	def init_buffer (self):
		# do this job will be executed in body_expected ()
		pass
		
	def is_gzip_compressed (self):
		return self.gzip_compressed
	
	def close (self):
		self.client_request.producer = None
		try: self.u.data = []
		except AttributeError: pass		
		#self.asyncon.disconnect ()		
		#self.asyncon.end_tran ()
		self.asyncon.handle_close (710, "Channel Closed")
			
	def affluent (self):
		# if channel doesn't consume data, delay recv data
		return len (self.u.data) < 1000
		
	def ready (self):
		# if exist consumable data or wait		
		return len (self.u.data) or self.got_all_data
		
	def more (self):
		self.flushed_time = time.time ()
		return self.u.read ()