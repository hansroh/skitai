from . import eurl
from . import localstorage
from skitai.protocol.http import request as http_request
from skitai.protocol.http import response as http_response
from skitai.protocol.http import request_handler as http_request_handler
from skitai.protocol.http import tunnel_handler
from skitai.protocol.ws import request_handler as ws_request_handler
from skitai.protocol.ws import tunnel_handler as ws_tunnel_handler
from skitai.protocol.ws import request as ws_request
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
_latest = ""
_map = asyncore.socket_map
_logger = None
_debug = False
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
	use_lifetime = True,
	debug = False
	):
	
	global _logger, _max_numpool, _current_numpool, _concurrents, _default_option, _configured, _use_lifetime, _timeout, _debug
	
	_default_option = default_option
	_max_numpool = numpool + 1
	_current_numpool = _max_numpool
	_logger = logger
	_concurrents = concurrents
	_use_lifetime = use_lifetime
	_debug = debug
	
	http_response.Response.SIZE_LIMIT = response_max_size
	localstorage.create (logger)
		
	socketpool.create (logger)
	adns.init (logger)
	trigger.start_trigger () # for keeping lifetime loop
			
	
def add (thing, callback, front = False):
	global _que, _default_header, _logger, _current_numpool, _currents
	
	if strutil.is_str_like (thing):
		thing = thing + " " + _default_option
		try:
			thing = eurl.EURL (thing)
		except:
			_logger.trace ()
			return
	
	if front:
		_que.insert (0, (thing, callback, _logger))
	else:	
		_que.append ((thing, callback, _logger))
		
	# notify new item
	if thing ["netloc"] not in _currents:
		_current_numpool += 1
	
	if _latest: # after loop started, not during queueing
		maybe_pop ()

def maybe_pop ():
	global _max_numpool, _current_numpool, _que, _map, _concurrents
	global _logger, _use_lifetime, _debug, _currents, _latest
	
	lm = len (_map)
	if _use_lifetime and not _que and lm == 1:
		lifetime.shutdown (0, 1)
		return
	
	if _current_numpool > _max_numpool:
		_current_numpool = _max_numpool  # maximum
	
	_currents = {}
	for r in list (_map.values ()):
		if isinstance (r, asynconnect.AsynConnect) and r.handler: 
			netloc = r.handler.request.el ["netloc"]			
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
		if _currents.get (el ["netloc"], 0) < _concurrents:
			try: 
				_currents [el ["netloc"]] += 1
			except KeyError:
				_currents [el ["netloc"]] = 1
			indexes.append (index)
			lm += 1
		index += 1
	
	if _debug:
		print (">>>>>>>>>>>> numpool:%d in map:%d queue:%d" % (_current_numpool, len (_map), len (_que)))
	
	pup = 0
	for index in indexes:
		item = _que.pop (index - pup)		
		Item (*item)		
		pup += 1

	if pup:
		# for multi threading mode
		trigger.the_trigger.pull_trigger ()
	
	return pup	

def get_all ():
	import time
	global _use_lifetime, _map, _que, _logger, _concurrent
	
	if not _que:
		_logger ("[warn] no item to get")
		return
	
	for i in range (_current_numpool):
		if not maybe_pop ():
			break
	
	if not _use_lifetime: 
		return
	
	try:
		lifetime.loop (3.0)
	finally:	
		socketpool.cleanup ()


class SSLProxyTunnelHandler (tunnel_handler.SSLProxyTunnelHandler):
	def get_handshaking_buffer (self):	
		req = ("CONNECT %s:%d HTTP/%s\r\nUser-Agent: %s\r\n\r\n" % (
					self.request.el ["netloc"], 
					self.request.el ["port"],
					self.request.el ["http-version"],
					self.request.el.get_useragent ()
				)).encode ("utf8")
		return req
		
class WSSSLProxyTunnelHandler (SSLProxyTunnelHandler, ws_tunnel_handler.SSLProxyTunnelHandler):
	pass

class WSProxyTunnelHandler (ws_tunnel_handler.ProxyTunnelHandler, SSLProxyTunnelHandler):
	def get_handshaking_buffer (self):	
		return SSLProxyTunnelHandler.get_handshaking_buffer (self)


class HTTPRequest (http_request.HTTPRequest):
	def __init__ (self, el, logger = None):		
		self.el = el			
		url = self.el ["rfc"]
		method = self.el ["method"].upper ()
		http_request.HTTPRequest.__init__ (self, url, method, headers = self.el.get_header (), logger = logger)
			
	def split (self, uri):
		return (self.el ["netloc"], self.el ["port"]), self.el ["uri"]
		
	def serialize (self):
		pass
		
	def get_auth (self):
		return self.el ["http-auth"]
			
	def get_data (self):
		if self.el ["scheme"] in ("ws", "wss"): return b""
		return self.el ["http-form"] is not None and self.el ["http-form"].encode ("utf8") or b""

	def get_eurl (self):
		return self.el
	
	def get_useragent (self):
		return self.el ["http-user-agent"]	
		

class WSRequest (HTTPRequest, ws_request.Request):
	def __init__ (self, el, logger = None):
		self.el = el
		ws_request.Request.__init__ (self, self.el ["rfc"], self.el ["wsoc-message"], self.el ["wsoc-opcode"], self.el ["http-auth"], logger = logger)
		
		
class Item:
	def __init__ (self, thing, callback, logger = None):
		global _logger, _timeout
		
		if localstorage.localstorage is None:
			configure (logger)
		
		if strutil.is_str_like (thing):
			self.el = eurl.EURL (thing)
		else:
			self.el = thing
			
		if logger:
			self.logger = logger			
		else:
			self.logger = _logger
		self.callback = callback
		
		if self.el ["scheme"] in ("ws", "wss"):
			self.el ['http-connection'] = "keep-aluve, Upgrade"			
			self.el.to_version_11 ()
			request = WSRequest (self.el, logger = self.logger)
			# websocket proxy should be tunnel
			if self.el.has_key ("http-proxy"):
				self.el ["http-tunnel"] = self.el ["http-proxy"]
				del self.el ["http-proxy"]
			if self.el.has_key ("http-tunnel"):
				if self.el ['scheme'] == 'wss':
					handler_class = WSSSLProxyTunnelHandler				
				else:
					handler_class = WSProxyTunnelHandler		
			else:
				handler_class = ws_request_handler.RequestHandler
				
		else:
			request = HTTPRequest (self.el, logger = self.logger)
			if self.el.has_key ("http-tunnel"):		
				request.el.to_version_11 ()
				handler_class = SSLProxyTunnelHandler
			else:	
				handler_class = http_request_handler.RequestHandler
			
		sp = socketpool.socketpool		
		if request.el ["http-tunnel"]:
			asyncon = sp.get ("proxys://%s" % request.el ["http-tunnel"])
		elif request.el ["http-proxy"]:
			asyncon = sp.get ("proxy://%s" % request.el ["http-proxy"])
		else:
			asyncon = sp.get (request.el ["rfc"])
					
		handler_class (asyncon, request, self.callback_wrap, request.el ["http-version"], request.el ['connection']).start ()
	
	def handle_websocket (self, handler):
		if handler.response.code == 101:
			request = WSRequest (handler.request.el, logger = self.logger)
			ws_request_handler.RequestHandler (asyncon, request, self.callback_wrap).start ()
		
	def callback_wrap (self, handler):
		global _latest
	
		r = rc.ResponseContainer (handler, self.callback)		
		_latest = r.uinfo.netloc
		# unkink back refs
		handler.asyncon = None
		handler.callback = None
		handler.response = None
		handler.request = None
		del handler
		
		try:
			self.callback (r)		
		except:
			_logger.trace ()
		maybe_pop ()
