import time
from skitai.server.threads import socket_map
from skitai.server.threads import trigger
import threading
from skitai.server.rpc import cluster_dist_call, rcache
from skitai.lib.attrdict import AttrDict

class OperationTimeout (Exception):
	pass

class	Result (rcache.Result):
	def __init__ (self, id, status, description = None, expt_class = None, expt_str = None, data = [], ident = None):
		rcache.Result.__init__ (self, status, ident)
		self.node = id
		self.__expt_class = expt_class
		self.__expt_str = expt_str
		# For Results competitable
		
		if status == 3:
			self.code, self.msg = 200, "OK"
		else:
			self.code, self.msg = 501, "Server Error"
		self.set_result (description, data)
	
	def __iter__ (self):
		return self.data.__iter__ ()
	
	def __slice__(self, start = None, end = None, step = None): 
		return self.data [slice(start, end, step)]
		
	def set_result (self, description, data):
		if not data:
			self.data = []
			return
			
		assert (len (description) == len (data [0]))		
		cols = [type (col) is tuple and col [0] or col.name for col in description]
		d = []
		for row in data:
			i = 0
			drow = AttrDict ()
			for name in cols:
				drow [name] = row [i]
				i += 1
			d.append (drow)
		self.data = d
		self.description = description
		
	def get_result (self):	
		return self.data
	
	def reraise (self):
		if self.__expt_class:
			raise self.__expt_class ("%s (status: %d)" % (self.__expt_str, self.status))
	
	def show_error (self):
		if self.__expt_class:
			return "%s %s" % (self.__expt_class, self.__expt_str)
		
	def cache (self, timeout = 300):
		if self.status != 3:
			return
		rcache.Result.cache (self, timeout)
	
			
class Dispatcher:
	def __init__ (self, cv, id, ident = None, filterfunc = None):
		self.__cv = cv
		self.id = id
		self.ident = ident
		self.filterfunc = filterfunc
		self.creation_time = time.time ()
		self.status = 0
		self.result = None
			
	def get_id (self):
		return self.id
	
	def get_status (self):
		# 0: Not Connected
		# 1: Operation Timeout
		# 2: Exception Occured
		# 3: Normal
		self.__cv.acquire ()		
		status = self.status
		self.__cv.release ()
		return status
		
	def set_status (self, code):
		self.__cv.acquire ()
		self.status = code
		self.__cv.notify ()
		self.__cv.release ()
		return code
		
	def get_result (self):
		if self.result is None:
			self.result = Result (self.id, 1, None, OperationTimeout, "Operation Timeout", None, self.ident)
			self.do_filter ()
		return self.result
	
	def do_filter (self):
		if self.filterfunc:
			self.filterfunc (self.result)
						
	def handle_result (self, description = None, expt_class = None, expt_str = None, data = None):
		if self.get_status () == 1:
			# timeout, ignore
			return
				
		if expt_class:
			status = 2			
		else:
			status = 3
		
		self.result = Result (self.id, status, description, expt_class, expt_str, data, self.ident)
		self.set_status (status)		
		        	     
#-----------------------------------------------------------
# Cluster Base Call
#-----------------------------------------------------------

class ClusterDistCall (cluster_dist_call.ClusterDistCall):
	def __init__ (self, 
		cluster,
		server, 
		dbname, 
		user, 
		password,
		dbtype,
		use_cache,
		mapreduce,
		callback,
		logger
		):
		
		self.server = server
		self.dbname = dbname
			
		self.user = user
		self.password = password
		self.dbtype = dbtype
		
		self._use_cache = use_cache		
		self._callback = callback		
		self._mapreduce = mapreduce		
		self._cluster = cluster
		self._cached_request_args = None
		self._cached_result = None
		
		self._logger = logger		
		self._requests = {}
		self._results = []
		self._canceled = 0
		self._init_time = time.time ()
		self._cv = None
		self._retry = 0	
		self._executed = False
		self._numnodes = 0
		
		self._sent_result = None
		
		if self._cluster:
			nodes = self._cluster.get_nodes ()
			self._numnodes = len (nodes)
			if self._mapreduce:
				self._nodes = nodes
			else: # anyone of nodes
				self._nodes = [None]
	
	def __getattr__ (self, name):	
		raise AttributeError("%s not found" % name)
		
	def _get_ident (self):
		cluster_name = self._cluster.get_name ()
		if cluster_name == "dbpool":
			_id = "%s/%s/%s/%s" % (self.server, self.dbname, self.user, self.password)
		else:
			_id = cluster_name
		_id += "/%s%s" % (
			self._cached_request_args [0],
			self._mapreduce and "/M" or ""
			)	
		return _id
				
	def _request (self, sql):
		self._cached_request_args = (sql,) # backup for retry
		
		if self._use_cache and rcache.the_rcache:
			self._cached_result = rcache.the_rcache.get (self._get_ident ())
			if self._cached_result is not None:
				return
		
		while self._avails ():
			asyncon = self._get_connection (None)			
			rs = Dispatcher (self._cv, asyncon.address, ident = not self._mapreduce and self._get_ident () or None, filterfunc = self._callback)
			self._requests [rs] = asyncon
			asyncon.execute (sql, rs.handle_result)
			
		trigger.wakeup ()
		
	def execute (self, sql):
		if self._executed:
			raise AssertionError ("Can't execute multiple, please create new connection")
		self._executed = True
		self._request (sql)
		
	def _get_connection (self, id = None):
		if id is None: id = self._nodes.pop ()
		else: self._nodes = []
			
		if self.server:
			asyncon = self._cluster.get (self.server, self.dbname, self.user, self.password, self.dbtype)		
		else:	
			asyncon = self._cluster.get (id)	
		
		if self._cv is None:
			self._cv = asyncon._cv
		return asyncon
	
	
class ClusterDistCallCreator:
	def __init__ (self, cluster, logger):
		self.cluster = cluster
		self.logger = logger
	
	def __getattr__ (self, name):	
		return getattr (self.cluster, name)
		
	def Server (self, server = None, dbname = None, user = None, password = None, dbtype = None, use_cache = True, mapreduce = False, callback = None):
		# reqtype: xmlrpc, rpc2, json, jsonrpc, http
		return ClusterDistCall (self.cluster, server, dbname, user, password, dbtype, use_cache, mapreduce, callback, self.logger)


		
	
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
