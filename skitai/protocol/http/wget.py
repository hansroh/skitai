from . import eurl
from . import request as http_request
from . import response as http_response
from . import request_handler as http_request_handler
from . import request_handler
from . import localstorage
from skitai.client import socketpool
from skitai import lifetime

_logger = None

def init (logger):
	global _logger
	_logger = logger
	socketpool.create (logger)
	localstorage.create (logger)

def close ():
	socketpool.cleanup ()


class Request (http_request.HTTPRequest):
	def __init__ (self, thing, data = {}, logger = None):
		if localstorage.localstorage is None:
			init_request (logger)
			
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

					
class add:
	def __init__ (self, thing, callback, logger = None):
		global _logger
		if logger:
			self.logger = logger			
		else:
			self.logger = _logger
		self.callback = callback

		request = Request (thing, logger = self.logger)
		sp = socketpool.socketpool
		if request.el ["http-connect"]:		
			request.el ["http-version"] = "1.1"
			try: del request.el ["connection"]
			except KeyError: pass
			request.el.del_header ("connection")
			asyncon = sp.get ("proxys://%s" % request.el ["http-connect"])				
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
		self.callback (handler.response)
				
		# unkink back refs
		handler.asyncon = None
		handler.callback = None
		handler.response = None
		handler.request = None
		del handler


def get_all ():
	lifetime.loop (3.0)

