import time
from skitai.server.threads import trigger
import threading
from skitai.protocol.http import request as http_request
from skitai.protocol.http import request_handler as http_request_handler
from skitai.protocol.http import response as http_response
from skitai.server import rcache


class Result (rcache.Result):
	def __init__ (self, id, status, response, ident = None):
		rcache.Result.__init__ (self, status, ident)		
		self.node = id
		self._response = response
		self.set_result ()
		
	def set_result(self):
		self.data = self._response.get_content ()
		self.header = self._response.header
		self.code = self._response.code
		self.msg = self._response.msg
		self.version = self._response.version
			
	def cache (self, timeout = 300):
		self._response = None
		if self.code != 200:
			return
		rcache.Result.cache (self, timeout)
		

class Results (rcache.Result):
	def __init__ (self, results, ident = None):
		self.results = results
		rcache.Result.__init__ (self, [rs.status for rs in self.results], ident)
		
	def __iter__ (self):
		return self.results.__iter__ ()

	def cache (self, timeout = 300):
		if self.is_cached:
			return
		if rcache.the_rcache is None or not self.ident: 
			return
		if [_f for _f in [rs.status != 3 or rs.code != 200 for rs in self.results] if _f]:
			return
		
		rcache.Result.__timeout = timeout
		rcache.Result.__cached_time = time.time ()
		
		rcache.the_rcache.cache (self)
		
			
class Dispatcher:
	def __init__ (self, cv, id, ident = None, filterfunc = None):
		self._cv = cv
		self.id = id
		self.ident = ident
		self.filterfunc = filterfunc
		self.creation_time = time.time ()
		self.status = 0		
		self.result = None
		self.handler = None		
			
	def get_id (self):
		return self.id
	
	def get_status (self):
		# 0: Not Connected
		# 1: Operation Timeout
		# 2: Exception Occured
		# 3: Normal
		self._cv.acquire ()		
		status = self.status
		self._cv.release ()
		return status
		
	def set_status (self, code):
		self._cv.acquire ()
		self.status = code
		self._cv.notify ()
		self._cv.release ()
		return code
		
	def get_result (self):
		if self.result is None: # timeout
			self.result = Result (self.id, 1, http_response.FailedResponse (70, "Timeout"), self.ident)				
			self.do_filter ()
		return self.result
	
	def do_filter (self):
		if self.filterfunc:
			self.filterfunc (self.result)
						
	def handle_result (self, handler):
		if self.get_status () == 1:
			# timeout, ignore
			return
	
		response = handler.response		
		
		# DON'T do_filter here, it blocks select loop
		
		if response.code >= 100:
			status = 3
		else:
			status = 2
		
		self.result = Result (self.id, status, response, self.ident)				
		self.set_status (status)
										
		handler.asyncon = None
		handler.callback = None
		handler.response = None
		
	
   	        	     
#-----------------------------------------------------------
# Cluster Base Call
#-----------------------------------------------------------
class _Method:
	def __init__(self, send, name):
		self.__send = send
		self.__name = name
		
	def __getattr__(self, name):
		return _Method(self.__send, "%s.%s" % (self.__name, name))
		
	def __call__(self, *args):
		return self.__send(self.__name, args)



class ClusterDistCall:
	def __init__ (self, 
		cluster, 
		uri,
		params = None,
		reqtype = "get",
		headers = None,
		login = None,
		encoding = None,		
		mapreduce = True,
		callback = None,
		logger = None
		):
		
		self._cluster = cluster
		self._uri = uri
		self._params = params
		self._headers = headers
		self._reqtype = reqtype
			
		self._login = login
		self._encoding = encoding
		self._mapreduce = mapreduce
		self._callback = callback
		self._logger = logger
	
		self._requests = {}
		self._results = []
		self._canceled = 0
		self._init_time = time.time ()
		self._cv = None
		self._retry = 0		
		self._cached_request_args = None		
		self._numnodes = 0
		self._cached_result = None
		
		if self._cluster:
			nodes = self._cluster.get_nodes ()
			self._numnodes = len (nodes)
			if self._mapreduce:
				self._nodes = nodes
			else: # anyone of nodes
				self._nodes = [None]
		
		if not self._reqtype.lower ().endswith ("rpc"):
			self._request ("", self._params)
		
	def __getattr__ (self, name):	  
		return _Method(self._request, name)
	
	def __del__ (self):
		self._cv = None
		self._results = []
	
	def get_ident (self):
		cluster_name = self._cluster.get_name ()
		if cluster_name == "socketpool":
			_id = "%s/%s" % (self._uri, self._reqtype)
		else:
			_id = "%s/%s/%s" % (cluster_name, self._uri, self._reqtype)
		_id += "/%s/%s" % self._cached_request_args
		_id += "%s" % (
			self._mapreduce and "/M" or ""			
			)
		return _id
				
	def _request (self, method, params):
		self._cached_request_args = (method, params) # backup for retry
		if rcache.the_rcache:
			self._cached_result = rcache.the_rcache.get (self.get_ident ())
			if self._cached_result is not None:
				return
		
		while self._avails ():
			if self._cluster.get_name () != "__socketpool__":
				asyncon = self._get_connection (None)
			else:
				asyncon = self._get_connection (self._uri)
			
			_reqtype = self._reqtype.lower ()
			rs = Dispatcher (self._cv, asyncon.address, ident = not self._mapreduce and self.get_ident () or None, filterfunc = self._callback)
			
			if _reqtype == "rpc":
				request = http_request.XMLRPCRequest (self._uri, method, params, self._headers, self._encoding, self._login, self._logger)				
			elif _reqtype == "jsonrpc":
				request = http_request.JSONRPCRequest (self._uri, method, params, self._headers, self._encoding, self._login, self._logger)		
			elif _reqtype == "upload": 
				request = http_request.HTTPMultipartRequest (self._uri, _reqtype, params, self._headers, self._encoding, self._login, self._logger)
			elif _reqtype == "put":
				request = http_request.HTTPPutRequest (self._uri, _reqtype, params, self._headers, self._encoding, self._login, self._logger)
			else: # "get", "post", "delete", ...
				request = http_request.HTTPRequest (self._uri, _reqtype, params, self._headers, self._encoding, self._login, self._logger)
			
			self._requests[rs] = asyncon
			r = http_request_handler.RequestHandler (asyncon, request, rs.handle_result)
			r.start ()
			
		trigger.wakeup ()
		
	def _avails (self):
		return len (self._nodes)
	
	def _get_connection (self, id = None):
		if id is None: id = self._nodes.pop ()
		else: self._nodes = []
		asyncon = self._cluster.get (id)
		if self._cv is None:
			self._cv = asyncon._cv
		return asyncon
			
	def _cancel (self):
		self._canceled = 1
	
	def getwait (self, timeout = 3):
		if self._cached_result is not None:
			return self._cached_result
			
		self._wait (timeout)
		if len (self._results) > 1:
			raise ValueError("Multiple Results, Use getswait")
		return self._results [0].get_result ()
	
	def getswait (self, timeout = 3):
		if self._cached_result is not None:
			return self._cached_result
			
		self._wait (timeout)
		return Results ([rs.get_result () for rs in self._results], ident = self.get_ident ())
	
	def _collect_result (self):
		for rs, asyncon in list(self._requests.items ()):
			status = rs.get_status ()
			if not self._mapreduce and status == 2 and self._retry < self._numnodes:
				self._logger ("cluster response error, switch to another...", "info")
				self._cluster.report (asyncon, False) # exception occured
				del self._requests [rs]
				self._retry += 1
				self._nodes = [None]
				self._request (*self._cached_request_args)
			
			elif status >= 2:
				del self._requests [rs]
				self._results.append (rs)
				if status == 2:
					self._cluster.report (asyncon, False) # exception occured
				else:	
					self._cluster.report (asyncon, True) # well-functioning
				rs.do_filter ()
					
	def _wait (self, timeout = 3):
		self._collect_result ()
		while self._requests and not self._canceled:
			remain = timeout - (time.time () - self._init_time)
			if remain <= 0: break						
			self._cv.acquire ()
			self._cv.wait (remain)
			self._cv.release ()
			self._collect_result ()
		
		# timeouts	
		for rs, asyncon in list(self._requests.items ()):
			asyncon.set_timeout (0) # make zombie channel
			asyncon.handle_timeout ()
			rs.set_status (1)
			self._cluster.report (asyncon, False) # maybe dead
			self._results.append (rs)
			del self._requests [rs]
		
	
class ClusterDistCallCreator:
	def __init__ (self, cluster, logger):
		self.cluster = cluster
		self.logger = logger
	
	def __getattr__ (self, name):	
		return getattr (self.cluster, name)
		
	def Server (self, uri, params = None, reqtype="rpc", headers = None, login = None, encoding = None, mapreduce = False, callback = None):
		# reqtype: rpc, get, post, head, put, delete
		return ClusterDistCall (self.cluster, uri, params, reqtype, headers, login, encoding, mapreduce, callback, self.logger)
		
	
if __name__ == "__main__":
	from skitai.lib  import logger
	from . import cluster_manager
	import sys
	import asyncore
	import time
	from skitai.client import socketpool
	
	def _reduce (asyncall):
		for rs in asyncall.getswait (5):
			print("Result:", rs.id, rs.status, rs.code, repr(rs.result [:60]))
					
	def testCluster ():	
		sc = cluster_manager.ClusterManager ("tt", ["210.116.122.187:3424 1", "210.116.122.184:3424 1", "175.115.53.148:3424 1"], logger= logger.screen_logger ())
		clustercall = ClusterDistCallCreator (sc, logger.screen_logger ())	
		s = clustercall.Server ("rpc2", login = "admin/whddlgkr")
		s.bladese.util.status ("openfos.v2")		
		threading.Thread (target = _reduce, args = (s,)).start ()
		
		while 1:
			asyncore.loop (timeout = 1, count = 2)
			if len (asyncore.socket_map) == 1:
				break
	
	def testSocketPool ():
		sc = socketpool.SocketPool (logger.screen_logger ())
		clustercall = ClusterDistCallCreator (sc, logger.screen_logger ())			
		s = clustercall.Server ("http://www.bidmain.com/")
		s.request ()
		
		#s = clustercall.Server ("http://210.116.122.187:3424/rpc2", "admin/whddlgkr")
		#s.bladese.util.status ("openfos.v2")
		
		threading.Thread (target = __reduce, args = (s,)).start ()
		
		while 1:
			asyncore.loop (timeout = 1, count = 2)
			print(asyncore.socket_map)
			if len (asyncore.socket_map) == 1:
				break
	
	trigger.start_trigger ()
	
	testCluster ()
	testSocketPool ()	
