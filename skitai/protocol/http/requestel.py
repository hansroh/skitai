from . import eurl
from . import request as http_request
from . import response as http_response
from . import request_handler as http_request_handler
from . import request_handler
from . import localstorage
from skitai.client import socketpool


def init (logger):
	socketpool.create (logger)
	localstorage.create (logger)

def close ():
	socketpool.cleanup ()


class Request (http_request.HTTPRequest):
	def __init__ (self, thing, data = {}, logger = None):
		if localstorage.localstorage is None:
			init_request (logger)
			
		if type (thing) is bytes:
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
		return self.el ["http-form"]

	def get_eurl (self):
		return self.el


class SSLProxyRequestHandler:
	def __init__ (self, asyncon, request, callback):
		self.asyncon = asyncon
		self.request = request
		self.callback = callback
		self.response = None
		self.buffer = b""
		asyncon.push (
			"CONNECT %s:%d HTTP/%s\r\nUser-Agent: %s\r\n\r\n" % (
				self.request.el ["netloc"], 
				self.request.el ["port"],
				self.request.el ["http-version"], 
				self.request.el.get_useragent ()
			)
		)
		asyncon.connect_with_adns ()
		
	def trace (self, name = None):
		if name is None:
			name = "proxys://%s:%d" % self.asyncon.address
		self.channel.trace (name)
		
	def log (self, message, type = "info"):
		uri = "proxys://%s:%d" % self.asyncon.address
		self.channel.log ("%s - %s" % (uri, message), type)
	
	def found_terminator (self):
		lines = self.buffer.decode ("utf8").split ("\r\n")		
		version, code, msg = http_response.crack_response (lines)
		if code == 200:
			self.asyncon.proxy_accepted = True
			http_request_handler.RequestHandler (
				self.asyncon, 
				self.request, 
				self.callback,
				self.request.el ["http_version"],
				self.request.el ["connetion"]
			)
					
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

				
class urlopen:
	def __init__ (thing, callback, logger = None):
		self.callback = callback

		r = Request (thing, logger = logger)
		if r.el ["http-proxy"]:
			if r.el ["scheme"] == "https":
				asyncon = socketpool.get ("proxys://%s" % r.el ["http-proxy"])				
				if not asyncon.connected:
					SSLProxyRequestHandler (asyncon, r, callback)
					return										
			else:
				asyncon = socketpool.get ("proxy://%s" % r.el ["http-proxy"])
						
		else:
			asyncon = socketpool.get (r.el ["rfc"]))			
			
		http_request_handler.RequestHandler (
			asyncon, 
			r, 
			self.callback_wrap,
			r.el ["http_version"],
			r.el ["connetion"]
		)
		
	def callback_wrap (self, handler):
		self.callback (handler.response)
				
		# unkink back refs
		handler.asyncon = None
		handler.callback = None
		handler.response = None
		handler.request = None
		del handler

		