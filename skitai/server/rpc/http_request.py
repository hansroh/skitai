try:
	import xmlrpclib as xmlrpclib
except ImportError:
	import xmlrpclib
	
import base64
try: 
	from urllib.parse import urlparse, quote
except ImportError:
	from urllib import quote
	from urlparse import urlparse
				
from . import http_response
from skitai.client import adns, asynconnect
from skitai.server import producers

JSONRPCLIB = True
try:
	import jsonrpclib
except ImportError:
	JSONRPCLIB = False
	
class XMLRPCRequest:
	content_type = "text/xml"
			
	def __init__ (self, uri, method, params = (), headers = None, encoding = "utf8", login = None, logger = None):
		self.uri = uri
		if uri.startswith ("http://") or uri.startswith ("https://"):
			self.url = self.make_url (uri)
		else:	
			self.url = uri
		self.method = method
		self.params = params
		self.headers = headers
		self.encoding = encoding
		self.login = login
		self.logger = logger
		self.data = self.serialize ()
	
	def get_method (self):
		return "POST"
		
	def make_url (self, uri):
		scheme, server, script, params, qs, fragment = urlparse (uri)
		if not script: script = "/"
		url = script
		if params: url += ";" + params
		if qs: url += "?" + qs
		return url
		
	def serialize (self):
		return xmlrpclib.dumps (self.params, self.method, encoding=self.encoding, allow_none=1)
		
	def set_address (self, address):
		self.address = address
			
	def get_auth (self):
		if self.login:
			return base64.encodestring (self.login) [:-1]
		
	def get_data (self):
		return self.data
			
	def get_content_type (self):
		if self.headers:
			for k, v in list(self.headers.items ()):
				if k.lower () == "content-length":
					del self.headers [k]
				elif k.lower () == "content-type":
					self.content_type = v
					del self.headers [k]					
		return self.content_type
	
	def get_headers (self):
		if self.headers:
			return list(self.headers.items ())
		else:
			return []	
			

if JSONRPCLIB:
	class JSONRPCRequest (XMLRPCRequest):
		content_type = "application/json-rpc"
		
		def serialize (self):
			return jsonrpclib.dumps (self.params, self.method, encoding=self.encoding, rpcid=None, version = "2.0")		

	
class HTTPRequest (XMLRPCRequest):
	content_type = "application/x-www-form-urlencoded"
	
	def __init__ (self, uri, method, formdata = {}, headers = None, login = None, logger = None):
		self.uri = uri
		self.method = method
		if uri.startswith ("http://") or uri.startswith ("https://"):
			self.url = self.make_url (uri)
		else:	
			self.url = uri
		
		self.formdata = formdata
		self.headers = headers
		self.login = login
		self.logger = logger
			
		self.data = self.serialize ()
	
	def get_method (self):
		return self.method.upper ()
					
	def serialize (self):
		# formdata type can be string, dict, boolean
		if not self.formdata:
			# no content, no content-type
			self.content_type = None		
			return ""

		if type (self.formdata) is type ({}):
			if self.get_content_type () != "application/x-www-form-urlencoded":
				raise TypeError ("POST Body should be string or can be encodable")
			return "&".join (["%s=%s" % (quote (k), quote (v)) for k, v in list(self.formdata.items ())])
			
		return self.formdata
		
	
class HTTPPutRequest (HTTPRequest):
	# PUT content-type hasn't got default type
	content_type = None
			
	def get_method (self):
		return "PUT"
					
	def serialize (self):
		if type (self.formdata) is not type (""):
			raise TypeError ("PUT body must be string")
		return self.formdata
		
		
class HTTPMultipartRequest (HTTPRequest):
	boundary = "-------------------SAE-20150614204358"
	
	def __init__ (self, uri, method, formdata = {}, headers = None, login = None, logger = None):
		HTTPRequest.__init__ (self, uri, method, formdata, headers, login, logger)
		if type (self.formdata) is type (""):
			self.find_boundary ()
	
	def get_method (self):
		return "POST"
						
	def get_content_type (self):
		HTTPRequest.get_content_type (self) # for remove content-type header
		return "multipart/form-data; boundary=" + self.boundary
			
	def find_boundary (self):
		s = self.formdata.find ("\r\n")
		if s == -1:
			raise ValueError("boundary not found")
		b = self.formdata [:s]			
		if b [:2] != "--":
			raise ValueError("invalid multipart/form-data")
		self.boundary = b [2:s]
		
	def serialize (self):
		if type (self.formdata) is type ({}):
			return producers.multipart_producer (self.formdata, self.boundary)
		return self.formdata


class Request:
	def __init__ (self, asyncon, request, callback, http_version = "1.1", connection = "keep-alive"):
		self.asyncon = asyncon
		request.set_address (self.asyncon.address)
		self.buffer = ""	
		self.wrap_in_chunk = False
		self.end_of_data = False		
		
		self.request = request
		self.callback = callback
		self.http_version = http_version
		self.logger = request.logger
		self.connection = connection		
		self.retry_count = 0
		self.response = None	
		self.asyncon.set_terminator (b"\r\n\r\n")	
	
	def _del_ (self):
		self.callback = None
		self.asyncon = None
		self.request = None
		self.response = None

	def log (self, message, type = "info"):
		self.logger.log ("%s - %s" % (self.request.uri, message), type)

	def log_info (self, message, type='info'):
		self.log (message, type)

	def trace (self):
		self.logger.trace (self.request.uri)
	
	#------------------------------------------------
	# handler must provide these methods
	#------------------------------------------------
	def get_request_buffer (self):
		data = self.request.get_data ()		
		is_data_producer = False
		
		hc = {}		
		hc ["Connection"] = self.connection
		
		if self.asyncon.address [1] in (80, 443):			
			hc ["Host"] = "%s" % self.asyncon.address [0]
		else:
			hc ["Host"] = "%s:%d" % self.asyncon.address
			
		hc ["Accept"] = "*/*"		
		hc ["Accept-Encoding"] = "gzip"
		
		if data:			
			try:
				cl = data.get_content_length ()
				is_data_producer = True
			except AttributeError:
				cl = len (data)				
			hc ["Content-Length"] = cl
		
		ct = self.request.get_content_type ()		
		if ct:
			hc ["Content-Type"] = self.request.get_content_type ()
			
		auth = self.request.get_auth ()
		if auth:
			hc ["Authorization"] = "Basic %s" % auth
		
		for k, v in self.request.get_headers ():
			hc [k] = v
		
		req = "%s %s HTTP/%s\r\n%s\r\n\r\n" % (
			self.request.get_method (),
			self.request.url,
			self.http_version,
			"\r\n".join (["%s: %s" % x for x in list(hc.items ())])
		)		
		if is_data_producer:
			return [req, data]
		else:	
			return [req + data]
	
	def recalibrate_response (self, error, msg):
		if self.response is None and not error and self.buffer: 
			s = self.buffer.find ("\n\n")
			if s != -1:
				body = self.buffer [s+2:]
				self.buffer = self.buffer [:s]
				try:
					self.create_response ()
					self.response.collect_incoming_data (body)							
				except:
					self.trace ()
					self.response = None
					error, msg = 40, "HTTP Header or Body Error"
					self.log ("%d %s" % (error, msg), "error")				
						
		if self.response is None:
			if error:
				self.response = http_response.FailedResponse (error, msg, self.request)
			else:
				error, msg = 41, "No Data"
				self.response = http_response.FailedResponse (error, msg, self.request)	
				self.log ("%d %s" % (error, msg), "error")
		
		# finally call done, even if failed or error occured in recving body, just done.
		self.response.done ()
		return error, msg
		
	def done (self, error = 0, msg = ""):		
		# handle abnormally raised exceptions like network error etc.
		self.recalibrate_response (error, msg)
				
		if self.asyncon:
			self.asyncon.request = None		
						
		if self.callback:
			self.callback (self)
		
	def collect_incoming_data (self, data):		
		if not self.response or self.asyncon.get_terminator () == "\r\n":
			self.buffer += data
		else:
			try:
				self.response.collect_incoming_data (data)
			except:
				self.response = http_response.FailedResponse (30, "Invalid Content", self.request)
				raise
			
	def found_terminator (self):
		if self.response:
			if self.end_of_data:
				self.asyncon.handle_close ()
				return
			
			if self.wrap_in_chunk:
				if self.asyncon.get_terminator () == 0:
					self.asyncon.set_terminator (b"\r\n")
					self.buffer = ""
					return
						
				if not self.buffer:
					return
										
				chunked_size = int (self.buffer.split (";") [0], 16)
				self.buffer = ""
				
				if chunked_size == 0:
					self.end_of_data = True
					self.asyncon.set_terminator (b"\r\n")
					
				elif chunked_size > 0:
					self.asyncon.set_terminator (chunked_size)
			
			elif self.asyncon.get_terminator () == 0:
				self.asyncon.handle_close ()
						
		else:
			try:
				self.create_response ()
			except:	
				# I don't know why handle exception here.
				# If not, recv data continuously T.T
				self.asyncon.handle_error ()
				return
			
			# 100 Continue etc. try recv continued header
			if self.response is None:
				return
				
			self.asyncon.close_it = self.will_be_close ()			
			if self.used_chunk ():
				self.wrap_in_chunk = True
				self.asyncon.set_terminator (b"\r\n") #chunked transfer
			
			else:			
				try:
					clen = self.get_content_length ()
				except TypeError:
					if self.asyncon.close_it:
						clen = ""
					else:
						clen = 0 # no transfer-encoding, no content-lenth
				
				if clen == 0:
					self.asyncon.handle_close ()
					return
					
				self.asyncon.set_terminator (clen)
			
			#self.buffer = ""

	def create_response (self):
		# overide for new Response
		buffer, self.buffer = self.buffer, ""
		try:
			self.response = http_response.Response (self.request, buffer)		
		except:
			self.log ("response header error: `%s`" % repr (buffer [:80]), "error")
			raise		
		self.is_continue_response ()
		
	def is_continue_response (self):	
		# default header never has "Expect: 100-continue"
		# ignore, wait next message	
		if self.response.code == 100:			
			self.response = None
			self.asyncon.set_terminator (b"\r\n\r\n")
			return True
		return False	
			
	def start (self):
		if adns.query:
			adns.query (self.asyncon.address [0], "A", callback = self.continue_start)
		else:
			self.continue_start (True)
		
	def continue_start (self, answer):
		if not answer:
			self.log ("DNS not found - %s" % self.asyncon.address [0], "error")
			return self.done (20, "DNS Not Found")			
		
		for buf in self.get_request_buffer ():
			self.asyncon.push (buf)
		self.asyncon.start_request (self)
	
	def retry (self):
		if self.retry_count: 
			return False		
		self.asyncon.request = None # unlink back ref.		
		self.retry_count = 1
		for buf in self.get_request_buffer ():
			self.asyncon.push (buf)
		self.asyncon.start_request (self)
		return True
					
	def will_be_close (self):
		if self.response is None:
			return True
		
		if self.connection == "close": #server misbehavior ex.paxnet
			return True
				
		close_it = True
		connection = self.response.get_header ("connection")
		if self.response.version in ("1.1", "1.x"):
			if not connection or connection.lower () == "keep-alive":
				close_it = False
		else:
			if connection and connection.lower () == "keep-alive":
				close_it = False
		
		if not close_it:
			keep_alive = self.response.get_header ("keep-alive")
			if keep_alive:
				for each in keep_alive.split (","):
					try: 
						k, v = each.split ("=", 1)
					except ValueError:
						continue
					
					if k.strip () == "timeout": 
						self.asyncon.keep_alive = int (v)
					elif k.strip () == "max" and int (v) == 0:
						close_it = True
		
		return close_it
	
	def used_chunk (self):
		transfer_encoding = self.response.get_header ("transfer-encoding")
		return transfer_encoding and transfer_encoding.lower () == "chunked"
	
	def get_content_length (self):
		return int (self.response.get_header ("content-length"))
	
	def get_content_type (self):
		return self.response.get_header ("content-type")
		
	def get_http_version (self):
		return self.response.version
   	
   	
   	