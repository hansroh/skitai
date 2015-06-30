import re
import xmlrpclib
from skitai.server import compressors, http_date
import time

JSONRPCLIB = True
try:
	import jsonrpclib
except ImportError:
	JSONRPCLIB = False

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
		d = ""
		if self.data:
			d = self.data.pop (0)
		if self.cache:
			self.cdata.append (d)
		return d
	
	def close(self):
		if self.cdata:
			return ''.join(self.cdata)
		return ''.join(self.data)
	
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
		header = header.split ("\r\n")
		self.response = header [0]
		self.header = header [1:]
		self._header_cache = {}
		self.version, self.code, self.msg = crack_response (self.response)
		self.size = 0
		self.got_all_data = False
		self.max_age = 0
		
		request_content_type = request.get_content_type ()
		current_content_type = self.get_header ("content-type")
		if current_content_type.startswith ("text/xml") or request_content_type == "text/xml": # by blade rpc2
			self.reqtype = "rpc2"
			self.p, self.u = xmlrpclib.getparser()
		elif current_content_type.startswith ("apllication/json-rpc"):
			self.reqtype = "rpc3"
			self.p, self.u = getfakeparser ()
		else:
			self.reqtype = "html"			
			self.set_max_age ()			
			self.p, self.u = getfakeparser (cache = self.max_age)			
					
		self.set_decompressor ()
	
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
			
	def set_decompressor (self):	
		self.decompressor = None
		if self.get_header ("Content-Encoding") == "gzip":
			self.decompressor = compressors.GZipDecompressor ()
			
	def collect_incoming_data (self, data):
		if self.decompressor:
			data = self.decompressor.decompress (data)
			
		self.size += len (data)
		if self.max_age and self.size > self.SIZE_LIMIT:
			self.max_age = 0
			self.u.no_cache ()
		
		if data:
			# sometimes decopressor return "",
			# null byte is signal of producer's ending, so ignore.			
			self.p.feed (data)
			
	def get_header (self, header):
		header = header.lower()
		hc = self._header_cache
		if not hc.has_key (header):
			h = header + ':'
			hl = len(h)
			for line in self.header:
				if line [:hl].lower() == h:
					r = line [hl:].strip ()
					hc [header] = r
					return r
			hc [header] = None
			return None
		else:
			return hc[header]
	
	def get_headers (self):
		return self.header		
				
	def get_content (self):
		if self.code < 100:
			return
			
		self.p.close ()
		result = self.u.close()
		
		if 200 <= self.code < 300:
			if self.reqtype == "rpc2":
				if len(result) == 1:
					result = result [0]
				return result
			elif JSONRPCLIB and self.reqtype == "rpc3":
				result = jsonrpclib.loads (result)
				return result
		return result
	

class FailedResponse (Response):
	def __init__ (self, errcode, msg, request = None):
		self.version, self.code, self.msg = "1.0", errcode, msg
		self.request = request
		self.buffer = None
		self.got_all_data = True
		self.max_age = 0
				
	def collect_incoming_data (self, data):
		raise IOError, "This Is Failed Response"
	
	def more (self):
		return ""
		
	def get_content (self):
		return ""
	
	def done (self):
		pass
		