from . import eurl
from . import localstorage
from skitai.protocol.http import request as http_request
from skitai.protocol.http import response as http_response
from skitai.protocol.http import request_handler as http_request_handler
from skitai.protocol.dns import asyndns
from skitai.client import socketpool, asynconnect
from skitai.server.threads import trigger
from skitai.lib import strutil
from skitai import lifetime
import asyncore
from . import rc
import asyncore
from skitai.client import adns

_currents = {}
_map = asyncore.socket_map
_logger = None
_debug = True
_que = []
_max_numpool = 4
_current_numpool = 4
_concurrents = 2
_default_header = ""
_use_lifetime = True
_timeout = 30

def configure (
	logger = None, 
	numpool = 3,
	timeout = 30,
	concurrents = 2,
	default_option = "", 
	response_max_size = 100000000,
	use_lifetime = True
	):
	
	global _logger, _max_numpool, _current_numpool, _concurrents, _default_option, _configured, _use_lifetime, _timeout
	
	_default_option = default_option
	_max_numpool = numpool + 1
	_current_numpool = _max_numpool
	_logger = logger
	_concurrents = concurrents
	_use_lifetime = use_lifetime
	
	http_response.Response.SIZE_LIMIT = response_max_size
	localstorage.create (logger)
		
	socketpool.create (logger)
	adns.init (logger)
	trigger.start_trigger () # for keeping lifetime loop
			
	
def add (thing, callback):
	global _que, _default_header, _logger, _current_numpool, _currents
	
	if strutil.is_str_like (thing):
		thing = thing + " " + _default_option
		try:
			thing = eurl.EURL (thing)
		except:
			_logger.trace ()
			return
					
	_que.append ((thing, callback, _logger))
	# notify new item
	if thing ["netloc"] not in _currents:
		_current_numpool += 1
	maybe_pop ()

def maybe_pop ():
	global _max_numpool, _current_numpool, _que, _map, _concurrents, _logger, _use_lifetime, _debug, _currents
	
	lm = len (_map)
	if _use_lifetime and not _que and lm == 1:
		lifetime.shutdown (0, 1)
		return
	
	if _current_numpool > _max_numpool:
		_current_numpool = _max_numpool  # maximum
	
	_currents = {}
	for r in list (_map.values ()):
		if isinstance (r, asynconnect.AsynConnect) and r.request: 
			netloc = r.request.request.el ["netloc"]			
		elif isinstance (r, asyndns.async_dns): 
			netloc = r.qname						
		else:
			continue	
			
		try: _currents [netloc] += 1
		except KeyError: _currents [netloc] = 1
		
	index = 0
	indexes = []		
	while lm < _current_numpool and _que:
		try:
			item = _que [index]
		except IndexError:
			# for minimize cost to search new item by concurrents limitation
			_current_numpool = len (_currents) * _concurrents
			if _current_numpool < 2:
				_current_numpool = 2 # minmum	
			if _debug:
				print (">>>>>>>>>>>> resize numpool %d" % _current_numpool)
			break
		
		el = item [0]
		if _currents.get (el ["netloc"], 0) <= _concurrents:
			try: 
				_currents [el ["netloc"]] += 1
			except KeyError:
				_currents [el ["netloc"]] = 1
			indexes.append (index)
			lm += 1
		index += 1
	
	if _debug:
		print (_current_numpool, len (_map), len (_que))
	
	pup = 0
	for index in indexes:
		item = _que.pop (index - pup)		
		Item (*item)		
		pup += 1

	if pup:
		# for multi threading mode
		trigger.the_trigger.pull_trigger ()
		

def get_all ():
	import time
	global _use_lifetime, _map, _que, _logger
	
	if not _que:
		_logger ("[warn] no item to get")
		return
	
	for r in list (_map.values ()):
		# reinit for loading _que too long
		r.event_time = time.time ()		
	
	if not _use_lifetime: 
		return
	
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
			
		if strutil.is_str_like (thing):
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
		global _logger, _timeout
		
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
			asyncon.set_network_delay_timeout (_timeout)
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
		r = rc.ResponseContainer (handler, self.callback)
		
		# unkink back refs
		handler.asyncon = None
		handler.callback = None
		handler.response = None
		handler.request = None
		del handler
		
		self.callback (r)
		maybe_pop ()
