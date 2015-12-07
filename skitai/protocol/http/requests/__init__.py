from . import eurl
from . import localstorage
from .. import request as http_request
from .. import response as http_response
from .. import request_handler as http_request_handler
from skitai.client import socketpool, asynconnect
from skitai import lifetime
import asyncore
import json
try:
	import xmlrpclib
except ImportError:
	import xmlrpc.client as xmlrpclib

_map = asyncore.socket_map
_logger = None
_que = []
_numpool = 4
_default_header = ""

def configure (logger = None, numpool = 3, default_timeout = 30, default_header = ""):
	global _logger, _numpool, _default_header
	
	asynconnect.set_timeout (default_timeout)
	_default_header = default_header
	_numpool = numpool + 1
	_logger = logger
	socketpool.create (logger)
	localstorage.create (logger)

def add (thing, callback, logger = None):
	global _que, _default_header
	
	if type (thing) is str:
		thing = thing + " " + _default_header
	_que.append ((thing, callback, logger))
	pop ()

def pop ():	
	global _numpool, _que
	
	lm = len (_map)
	while lm < _numpool and _que:
		item = _que.pop (0)
		Item (*item)
		lm += 1
	
def get_all ():
	try:
		lifetime.loop (3.0)
	finally:	
		socketpool.cleanup ()


class Request (http_request.HTTPRequest):
	def __init__ (self, thing, data = {}, logger = None):
		if localstorage.localstorage is None:
			configure (logger)
			
		if type (thing) is str:
			self.el = eurl.EURL (thing, data)
		else:
			self.el = thing

		http_request.HTTPRequest.__init__ (
			self, 
			self.el ["rfc"], 
			self.el ["method"].upper (), 
			headers = self.el.get_header (),
			logger = logger
			)
			
	def split (self, uri):
		return (self.el ["netloc"], self.el ["port"]), self.el ["uri"]
		
	def serialize (self):
		pass
		
	def get_auth (self):
		return self.el ["auth"]
		
	def get_data (self):
		return self.el ["http-form"] is not None and self.el ["http-form"].encode ("utf8") or b""

	def get_eurl (self):
		return self.el


class SSLProxyRequestHandler:
	def __init__ (self, asyncon, request, callback):
		self.asyncon = asyncon
		self.request = request
		self.callback = callback
		self.response = None
		self.buffer = b""
		
		asyncon.set_terminator (b"\r\n\r\n")
		asyncon.push (
			("CONNECT %s:%d HTTP/%s\r\nUser-Agent: %s\r\n\r\n" % (
				self.request.el ["netloc"], 
				self.request.el ["port"],
				self.request.el ["http-version"], 
				self.request.el.get_useragent ()
			)).encode ("utf8")
		)
		asyncon.connect_with_adns ()
		
	def trace (self, name = None):
		if name is None:
			name = "proxys://%s:%d" % self.asyncon.address
		self.request.logger.trace (name)
		
	def log (self, message, type = "info"):
		uri = "proxys://%s:%d" % self.asyncon.address
		self.request.logger.log ("%s - %s" % (uri, message), type)
	
	def found_terminator (self):
		lines = self.buffer.split ("\r\n")
		version, code, msg = http_response.crack_response (lines [0])
		if code == 200:
			self.asyncon.proxy_accepted = True
			http_request_handler.RequestHandler (
				self.asyncon, 
				self.request, 
				self.callback,
				self.request.el ["http-version"],				
				self.request.el.get_connection ()
			).start ()
		else:
			self.done (31, "%d %s Occured" % (code, msg))
	
	def done (self, code, msg):
		if code:
			self.asyncon.request = None # unlink back ref
			self.respone = http_response.FailedResponse (code, msg, self.request)
			self.callback (self)
			
	def collect_incoming_data (self, data):
		self.buffer += data
		
	def retry (self):
		return False

	def abort (self):
		pass


class RCRequest:
	def __init__ (self, obj):
		self._header_cache = {}
		self.set (obj)
		
	def set (self, handler):	
		self.header = handler.header
		self.uri = handler.uri
		self.version = handler.http_version
		self.proxy = handler.request.el ["http-proxy"]
		self.connection = handler.request.el ["http-connection"]
		self.user_agent = handler.request.el ["http-user-agent"]
		
		self.body = handler.request.get_data ()
		self.content_type = handler.request.get_content_type ()
		self.encoding = handler.request.encoding
		
	def get_header (self, header):
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
			return None
		else:
			return hc[header]

class RCResponse (RCRequest):
	def set (self, handler):	
		r = handler.response
		self.header = r.header
		self.version, self.code, self.msg = r.version, r.code, r.msg
		
		self.content_type = None
		self.encoding = None
		
		ct = self.get_header ("content-type")
		if ct:
			ctl = ct.split (";")
			self.content_type = ctl [0]
			for param in ctl [1:]:
				if param.strip ().startswith ("charset="):
					self.encoding = param.split ("=", 1)[-1].strip ().lower ()
			
		self.connection = self.get_header ("connection")
		self.body = r.get_content ()		
	
	def json (self):
		return json.loads (self.body)
	
	def xmlrpc (self):
		return xmlrpclib.loads (self.body)	

class RCUInfo:
	def __init__ (self, eurl):
		self.eurl = eurl
		del self.eurl.data
	
	def __getattr__ (self, attr):
		try:
			return self.eurl [attr]
		except KeyError:
			raise AttributeError
				
class RCUData:
	def __init__ (self, eurl):
		self.user = eurl.user
	
	def __getattr__ (self, attr):
		try:
			return self.user [attr]
		except KeyError:
			raise AttributeError
				
class ResponseContainer:
	def __init__ (self, handler):
		self.uinfo = RCUInfo (handler.request.el)
		self.udata = RCUData (handler.request.el)
		self.request = RCRequest (handler)
		self.response = RCResponse (handler)
		
		for header in handler.response.get_headers ():
			if header.lower ().startswith ("set-cookie: "):
				localstorage.localstorage.set_cookie_from_string (
					handler.response.request.el ["rfc"],
					header [12:]
				)
	
	def set_cookie (self, k, v):
		localstorage.localstorage.set_cookie (self.uinfo.rfc, k, v)
	
	def get_cookie (self, k):	
		localstorage.localstorage.get_cookie (self.uinfo.rfc, k)
	
	def set_item (self, k, v):
		localstorage.localstorage.set_item (self.uinfo.rfc, k, v)
	
	def get_item (self, k):	
		localstorage.localstorage.get_item (self.uinfo.rfc, k)
	
	def advance (self, surl):
		return self.uinfo.eurl.advance (surl)


class Item:
	def __init__ (self, thing, callback, logger = None):
		global _logger
		if logger:
			self.logger = logger			
		else:
			self.logger = _logger
		self.callback = callback
	
		request = Request (thing, logger = self.logger)
		sp = socketpool.socketpool
		if request.el ["http-tunnel"]:		
			request.el.to_version_11 ()
			asyncon = sp.get ("proxys://%s" % request.el ["http-tunnel"])				
			if not asyncon.connected:
				asyncon.request = SSLProxyRequestHandler (asyncon, request, self.callback_wrap)
				return				
		
		elif request.el ["http-proxy"]:
			asyncon = sp.get ("proxy://%s" % request.el ["http-proxy"])
		
		else:
			asyncon = sp.get (request.el ["rfc"])			
			
		http_request_handler.RequestHandler (
			asyncon, 
			request, 
			self.callback_wrap,
			request.el ["http-version"],
			request.el.get_connection ()
		).start ()
		
	def callback_wrap (self, handler):
		rc = ResponseContainer (handler)
		
		# unkink back refs
		handler.asyncon = None
		handler.callback = None
		handler.response = None
		handler.request = None
		del handler
		
		self.callback (rc)		
		pop ()
