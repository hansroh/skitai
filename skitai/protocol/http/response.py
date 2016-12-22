import re
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
from skitai.server import http_date
from skitai.lib import compressors
import time


class RepsonseError (Exception): 
	pass

RESPONSE = re.compile ('HTTP/([0-9.]+) ([0-9]{3})\s?(.*)')
def crack_response (data):
	global RESPONSE
	[ version, code, msg ] = RESPONSE.findall(data)[0]
	return version, int(code), msg

#------------------------------------------------------
# xmlrpclib like json fakes
#------------------------------------------------------
class FakeParser(object):
	def __init__(self, target):
		self.target = target

	def feed(self, data):
		self.target.feed(data)

	def close(self):
		pass


class FakeTarget(object):
	def __init__(self, cache = False):
		self.cache = cache
		self.data = []
		self.cdata = []

	def feed(self, data):
		self.data.append(data)
	
	def read (self):
		d = b""
		if self.data:
			d = self.data.pop (0)
		if self.cache:
			self.cdata.append (d)
		return d
	
	def close(self):
		if self.cdata:
			return b''.join(self.cdata)
		return b''.join(self.data)
	
	def no_cache (self):
		self.cache = False
		self.cdata = []
		
		
def getfakeparser (cache = False):
	target = FakeTarget(cache)
	return FakeParser(target), target


class Response:
	SIZE_LIMIT = 2**19
	
	def __init__ (self, request, header):		
		self.request = request		
		if header [:2] == "\r\n":
			header = header [2:]
		header = header.split ("\r\n")	
		self.response = header [0]
		self.header = header [1:]
		self._header_cache = {}
		self.version, self.code, self.msg = crack_response (self.response)
		self.size = 0
		self.got_all_data = False
		self.reqtype = None
		self.max_age = 0
		self.decompressor = None
		
	def set_max_age (self):
		self.max_age = 0
		if self.code != 200:
			return
		
		if self.get_header ("set-cookie"):
			return
		
		expires = self.get_header ("expires")		
		if expires:
			try:
				val = http_date.parse_http_date (expires)
			except:
				val = 0
	
			if val:
				max_age = val - time.time ()
				if max_age > 0:
					self.max_age = int (max_age)
					return
	
		cache_control = self.get_header ("cache-control")
		if not cache_control:
			return
			
		for each in cache_control.split (","):			
			try: 
				k, v = each.split("=")					
				if k.strip () == "max-age":
					max_age  = int (v)
					if max_age > 0:
						self.max_age = max_age
						break
			except ValueError: 
				continue
		
		if self.max_age > 0:
			age = self.get_header ("age")
			if age:
				try: age = int (age)	
				except: pass	
				else:
					self.max_age -= age
				
	def done (self):
		# it must be called finally
		self.got_all_data = True
		
		if self.decompressor:
			try:
				data = self.decompressor.flush ()
			except:					
				pass
			else:
				self.p.feed (data)			
			self.decompressor = None
	
	def init_buffer (self):
		request_content_type = self.request.get_content_type ()
		current_content_type = self.get_header ("content-type")
		if current_content_type is None:
			current_content_type = ""
			
		if self.request.xmlrpc_serialized ():
			self.reqtype = "XMLRPC"
			self.p, self.u = xmlrpclib.getparser()		
		else:
			self.reqtype = "HTTP"
			self.set_max_age ()			
			self.p, self.u = getfakeparser (cache = self.max_age)					

		if self.get_header ("Content-Encoding") == "gzip":			
			self.decompressor = compressors.GZipDecompressor ()
			
	def collect_incoming_data (self, data):
		if self.size == 0:
			self.init_buffer ()		
		self.size += len (data)
			
		#print ("<<<<<", repr (data)[-80:], len (data) )	
		if self.decompressor:
			data = self.decompressor.decompress (data)
		
		if self.max_age and self.size > self.SIZE_LIMIT:
			self.max_age = 0
			self.u.no_cache ()
		
		#print (">>>>>", repr (data)[-80:])
		if data:
			# sometimes decompressor return "",
			# null byte is signal of producer's ending, so ignore.
			self.p.feed (data)
	
	def get_header_with_attr (self, header, default = None):
		d = {}
		v = self.get_header (header)
		if v is None:
			return default, d
			
		v2 = v.split (";")
		if len (v2) == 1:
			return v, d
		for each in v2 [1:]:
			try:
				a, b = each.strip ().split ("=", 1)
			except ValueError:
				a, b = each.strip (), None
			d [a] = b
		return v2 [0], d	
				
	def get_header (self, header = None, default = None):
		if header is None:
			return self.header
		header = header.lower()
		hc = self._header_cache
		if header not in hc:
			h = header + ':'
			hl = len(h)
			for line in self.header:
				if line [:hl].lower() == h:
					r = line [hl:].strip ()
					hc [header] = r
					return r
			hc [header] = None
			return default
		else:
			return hc[header] is not None and hc[header] or default
	
	def get_headers (self):
		return self.header
	
	def get_content (self):
		if self.code >= 700:
			return None
		
		if self.size == 0:
			return b""
				
		self.p.close ()
		result = self.u.close()
		if 200 <= self.code < 300:
			if self.reqtype == "XMLRPC":
				if len(result) == 1:
					result = result [0]
				return result
				
		return result
	

class FailedResponse (Response):
	def __init__ (self, errcode, msg, request = None):
		self.version, self.code, self.msg, self.header = "1.0", errcode, msg, []
		self.request = request
		self.buffer = None
		self.got_all_data = True
		self.max_age = 0
				
	def collect_incoming_data (self, data):
		raise IOError("This Is Failed Response")
	
	def more (self):
		return b""
		
	def get_content (self):
		return b""
	
	def done (self):
		pass
		