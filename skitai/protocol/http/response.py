import zlib
import re
from skitai.server import compressors

class RepsonseError (Exception): pass

RESPONSE = re.compile ('HTTP/([0-9.]+) ([0-9]{3})\s?(.*)')
def crack_response (data):
	global RESPONSE
	[ version, code, msg ] = RESPONSE.findall(data)[0]
	return version, int(code), msg


class Response:
	SIZE_LIMIT = 2**24
	def __init__ (self, eurl, header, localstorage):	
		self.buffer = ""
		self.size = 0
		self.decompressor = None
		self.localstorage = localstorage	
		self.eurl = eurl		
		
		header = header.split ("\r\n")
		try:
			self.version, self.code, self.msg = crack_response (header [0])
			
		except IndexError: # crazy, no header if 200
			self.version, self.code, self.msg = "1.1", 200, "OK"
			self.response = "HTTP/1.1 200 OK"
			self.header = []
			self.collect_incoming_data ("\r\n".join (header))		
				
		else:	
			self.response = header [0]
			self.header = header [1:]		
			if self.localstorage:
				for cookie in self.get_headers ("Set-Cookie"):
					self.localstorage.set_cookie (self.eurl ["url"], cookie)
			
			content_encoding = self.get_header ("Content-Encoding")
			if content_encoding == "gzip":
				self.decompressor = compressors.GZipDecompressor ()				
			elif content_encoding == "deflate":
				self.decompressor = zlib.decompressobj ()
			
	def get_header (self, header = None):
		h = self.get_headers (header)
		if not h: 
			return None
		return h [0]
	
	def get_headers (self, header):
		vals = []
		for line in self.header:
			key, val = line.split (":", 1)			
			if key.lower () == header.lower ():
				vals.append (val.strip ())
		return vals
		
	def collect_incoming_data (self, data):		
		if self.decompressor:
			data = self.decompressor.decompress (data)
		self.size += len (data)		
		if self.size > self.SIZE_LIMIT:
			self.buffer = None
			raise RepsonseError, "Content Oversize Error"		
		self.buffer += data
		
	def get_content (self):
		if self.decompressor:
			try:
				self.buffer += self.decompressor.flush ()
			except: 
				pass
		return self.buffer
		
	def get_response (self):
		return self.version, self.code, self.msg
	
	def __del__ (self):
		self.close ()
		
	def close (self, error = None, msg = ""):
		self.buffer = None


class FailedResponse (Response):
	def __init__ (self, errcode, errmsg, eurl):
		self.version, self.code, self.msg = "1.1", errcode, errmsg
		self.eurl = eurl
		self.buffer = None
	
	def get_content (self):
		return 
		
	def collect_incoming_data (self, data):
		raise IOError, "This Is Failed Response"
	