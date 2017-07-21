import pytest, os
from mock import MagicMock
import socket
import multiprocessing, threading
from base64 import b64encode

from aquests.lib.athreads import threadlib
from aquests.protocols.http import http_util, request, response
from aquests.protocols.grpc import request as grpc_request
from aquests.protocols.ws import request as ws_request, response as ws_response

import skitai
from skitai import was as the_was
from skitai.server.http_request import http_request
from skitai.server.wastuff import triple_logger
from skitai.server.http_server import http_server, http_channel
from skitai.server.handlers import pingpong_handler, proxy_handler
from skitai.server import wsgiappservice
from skitai.server.handlers.websocket import servers as websocekts
from skitai.server.handlers import vhost_handler

#---------------------------------------------

def getroot ():
	return os.path.join (os.path.dirname (__file__), "examples")	
	
def rprint (*args):
	print ('++++++++++', *args)

def assert_request (h, r, expect_code):
	assert h.match (r)	
	h.handle_request (r)
	if r.command in ('post', 'put', 'patch'):
		r.collector.collect_incoming_data (r.payload)
		r.collector.found_terminator ()			
	result = r.channel.socket.getvalue ()
	header, payload = result.split (b"\r\n\r\n", 1)
	resp = response.Response (request, header.decode ("utf8"))
	resp.collect_incoming_data (payload)
	#rprint (result)
	assert resp.status_code == expect_code
	return resp

#---------------------------------------------

def clear_handler (wasc):
	# reset handler
	wasc.httpserver.handlers = []
	
def install_vhost_handler (wasc, apigateway = 0, apigateway_authenticate = 0):
	clear_handler (wasc)			
	static_max_ages = {"/img": 3600}	
	enable_apigateway = apigateway
	apigateway_authenticate = apigateway_authenticate 
	apigateway_realm = "Pytest"
	apigateway_secret_key = "secret-pytest"	
	
	vh = wasc.add_handler (
		1, 
		vhost_handler.Handler, 
		wasc.clusters, 
		wasc.cachefs, 
		static_max_ages,
		enable_apigateway,
		apigateway_authenticate,
		apigateway_realm,
		apigateway_secret_key
	)	
	return vh

def install_proxy_handler (wasc):
	clear_handler (wasc)
	h = wasc.add_handler (
		1, 
		proxy_handler.Handler, 
		wasc.clusters, 
		wasc.cachefs, 
		False
	)	
	return h

#---------------------------------------------
	
def logger ():
	return triple_logger.Logger ("screen", None)	
	
def conn ():
	class Socket (MagicMock):
		def __init__ (self, *args, **karg):
			MagicMock.__init__ (self, *args, **karg)
			self.__buffer = []
		
		def send (self, data):
			self.__buffer.append (data)
			return len (data)
		
		def getvalue (self):	
			return b"".join (self.__buffer)
		
	sock = Socket (name="socket", spec=socket.socket)
	sock.fileno.return_value = 1	
	return sock
	
def server ():
	log = logger ()
	s = http_server ('0.0.0.0', 3000, log.get ("server"), log.get ("request"))	
	s.install_handler (pingpong_handler.Handler ())
	return s

def channel ():
	c = http_channel (server (), conn (), ('127.0.0.100', 65535))
	c.connected = True
	return c

def disable_threads ():	
	[the_was.queue.put (None) for each in range (the_was.numthreads)]
	the_was.queue = None
	the_was.threads = None
	the_was.numthreads = 0

def enable_threads (numthreads = 1):
	queue = threadlib.request_queue2 ()
	the_was.queue =  queue
	the_was.threads = threadlib.thread_pool (queue, numthreads, wasc.logger.get ("server"))
	the_was.numthreads = numthreads
	
wasc = wsgiappservice.WAS
wasc.register ("logger", logger ())
wasc.register ("httpserver", server ())
wasc.register ("debug", False)
wasc.register ("plock", multiprocessing.RLock ())
wasc.register ("clusters",  {})
wasc.register ("clusters_for_distcall",  {})
wasc.register ("workers", 1)
wasc.register ("cachefs", None)	
wasc.register ("lock", threading.RLock ())
websocekts.start_websocket (wasc)
wasc.register ("websockets", websocekts.websocket_servers)
wasc.numthreads = 0
skitai.start_was (wasc)

#---------------------------------------------

DEFAULT_HEADERS = {
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
	"Accept-Encoding": "gzip, deflate, br",
	"Accept-Language": "en-US,en;q=0.8,en-US;q=0.6,en;q=0.4",
	"Referer": "https://pypi.python.org/pypi/skitai",
	"Upgrade-Insecure-Requests": 1,
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
}

class Client:
	def override (self, headers):
		copied = DEFAULT_HEADERS.copy ()
		for k, v in headers:
			copied [k] = v
		return copied	
	
	def geneate (self, r):
		m, u, v = r.get_method (), r.path, r.http_version		
		headers = ["%s: %s" % each for each in r.get_headers ()]
		return http_request (channel (), "%s %s HTTP/%s" % (m, u, v), m.lower (), u, v, headers)
	
	def serialize (self, payload):	
		_payload = []
		while 1:
			d = payload.more ()
			if not d: break
			_payload.append (d)	
		return b"".join (_payload)
					
	def make_request (self, method, uri, data, headers, auth, meta, version = "1.1"):		
		headers = self.override (headers)
		if method == "UPLOAD":
			r = request.HTTPMultipartRequest (uri, "POST", data, headers, auth, None, meta, version)		
		else:	
			r = request.HTTPRequest (uri, method, data, headers, auth, None, meta, version)
		
		hr = self.geneate (r)		
		if data:
			payload = r.get_payload ()
			if method == "UPLOAD":
				payload = self.serialize (payload)
			hr.set_body (payload)
		return hr
	
	def get (self, uri, headers = [], auth = None, meta = {}, version = "1.1"):
		return self.make_request ("GET", uri, None, headers, auth, meta, version)
	
	def delete (self, uri, headers = [], auth = None, meta = {}, version = "1.1"):
		return self.make_request ("DELETE", uri, None, headers, auth, meta, version)
		
	def post (self, uri, data, headers = [], auth = None, meta = {}, version = "1.1"):
		return self.make_request ("POST", uri, data, headers, auth, meta, version)	
	
	def upload (self, uri, data, headers = [], auth = None, meta = {}, version = "1.1"):
		return self.make_request ("UPLOAD", uri, data, headers, auth, meta, version)	
	
	def patch (self, uri, data, headers = [], auth = None, meta = {}, version = "1.1"):
		return self.make_request ("PATCH", uri, data, headers, auth, meta, version)	
	
	def put (self, uri, data, headers = [], auth = None, meta = {}, version = "1.1"):
		return self.make_request ("PUT", uri, data, headers, auth, meta, version)	
	
	def xmlrpc (self, uri, method, data, headers = [], auth = None, meta = {}, version = "1.1"):
		r = request.XMLRPCRequest (uri, method, data, self.override (headers), auth, None, meta, version)
		hr = self.geneate (r)		
		hr.set_body (r.get_payload ())
		return hr
	
	def grpc (self, uri, method, data, headers = [], auth = None, meta = {}, version = "2.0"):		
		r = grpc_request.GRPCRequest (uri, method, data, self.override (headers), auth, None, meta, version)
		hr = self.geneate (r)	
		hr.set_body (self.serialize (r.get_payload ()))
		return hr
	
	def ws (self, uri, message, headers = [], auth = None, meta = {}, version = "1.1"):
		r = ws_request.Request (uri, message, self.override (headers), auth, None, meta, version)
		r.headers ['Origin'] = "http://%s:%d" % r.address
		r.headers ['Sec-WebSocket-Key'] = b64encode(os.urandom(16))
		r.headers ['Connection'] = "keep-alive, Upgrade"
		r.headers ['Upgrade'] = 'websocket'
		r.headers ['Cache-Control'] = 'no-cache'		
		r.method = "get"
		hr = self.geneate (r)
		hr.set_body (r.get_payload ().more ())
		return hr
			
client = Client ()

