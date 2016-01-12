from . import eurl
from . import localstorage
from .. import request as http_request
from .. import response as http_response
from .. import request_handler as http_request_handler
from skitai.client import socketpool, asynconnect
from skitai.server.threads import trigger
from skitai import lifetime
import asyncore
from . import rc
import asyncore
from skitai.client import adns

_map = asyncore.socket_map
_logger = None
_que = []
_numpool = 4
_concurrents = 2
_default_header = ""

def configure (
	logger = None, 
	numpool = 3,
	timeout = 30,
	concurrents = 2,
	default_option = "", 
	response_max_size = 100000000
	):
	
	global _logger, _numpool, _concurrents, _default_option, _configured
	
	asynconnect.set_timeout (timeout)		
	_default_option = default_option
	_numpool = numpool + 1
	_logger = logger
	_concurrents = concurrents
	http_response.Response.SIZE_LIMIT = response_max_size
	socketpool.create (logger)
	localstorage.create (logger)
	adns.init (logger)
	trigger.start_trigger () # for keeping lifetime loop	
		
	
def add (thing, callback, logger = None):
	global _que, _default_header
	
	if type (thing) is str:
		thing = thing + " " + _default_option
	_que.append ((thing, callback, logger))
	maybe_pop ()

def maybe_pop ():
	global _numpool, _que, _map, _concurrents, _logger
	
	if not _que:
		lifetime.shutdown (0, 1)
		return
	
	lm = len (_map)		
	if lm >= _numpool:
		return
	
	currents = {}
	for r in list (_map.values ()):
		try: currents [r.el ["netloc"]] += 1
		except KeyError: currents [r.el ["netloc"]] = 1
		except AttributeError: pass

	index = 0
	indexes = []	
	while lm < _numpool and _que:
		try:
			item = _que [index]
		except IndexError:
			break	
		if type (item [0]) is str:
			try: 
				el = eurl.EURL (item [0])
			except:
				_logger.trace ()
				indexes.append ((0, index))
				index += 1
				continue				
			else:					
				_que [index] = (el,) + item [1:]

		else:
			el = item [0]						
		if currents.get (el ["netloc"], 0) < _concurrents:
			indexes.append ((1, index))
			lm += 1
		index += 1
		
	pup = 0
	for valid, index in indexes:
		item = _que.pop (index - pup)
		if valid:
			Item (*item)
		pup += 1

def get_all ():
	try:
		lifetime.loop (3.0)
	finally:	
		socketpool.cleanup ()


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
			self.done (code, msg)
	
	def done (self, code, msg):
		if code:			
			self.asyncon.request = None # unlink back ref			
			self.respone = http_response.FailedResponse (code, msg, self.request)
			self.callback (self)
			
	def collect_incoming_data (self, data):
		self.buffer += data
		
	def retry (self):
		return False

	def close (self):
		self.buffer = b""		


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
		r = rc.ResponseContainer (handler)
		
		# unkink back refs
		handler.asyncon = None
		handler.callback = None
		handler.response = None
		handler.request = None
		del handler
		
		self.callback (r)
		maybe_pop ()
