import time
from aquests.lib.athreads import socket_map
from aquests.lib.athreads import trigger
import threading
from skitai.server.rpc import cluster_dist_call, rcache
from aquests.lib.attrdict import AttrDict
from aquests.dbapi import request
import asyncore
from skitai import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB

class OperationTimeout (Exception):
	pass

class RequestFailed (Exception):
	pass

class FailedRequest:
	def __init__ (self, expt_class, expt_msg):
		self.description = None
		self.data = None
		self.expt_class = None
		self.expt_str = None
		
		self.code, self.msg = 501, "timeout"
			
			
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
			if self.get_status () == -1:
				self.result = cluster_dist_call.Result (self.id, -1, FailedRequest (RequestFailed, "Request Failed"), self.ident)
			else:
				self.result = cluster_dist_call.Result (self.id, 1, FailedRequest (OperationTimeout, "Operation Timeout"), self.ident)
		return self.result
	
	def do_filter (self):
		if self.filterfunc:
			self.filterfunc (self.result)
						
	def handle_result (self, request):
		if self.get_status () == 1:
			# timeout, ignore
			return
				
		if request.expt_class:
			status = 2			
		else:
			status = 3
		
		self.result = cluster_dist_call.Result (self.id, status, request, self.ident)
		self.set_status (status)
		        	     
#-----------------------------------------------------------
# Cluster Base Call
#-----------------------------------------------------------

class ClusterDistCall (cluster_dist_call.ClusterDistCall):
	def __init__ (self, 
		cluster,
		server, 
		dbname, 
		auth,
		dbtype,
		use_cache,
		mapreduce,
		filter,
		callback,
		logger
		):
		
		self.server = server
		self.dbname = dbname
		
		self.auth = auth		
		self.dbtype = dbtype
		if self.dbtype == DB_PGSQL:
			if self.dbname in (DB_SQLITE3, DB_REDIS):
				self.dbtype = self.dbname
				self.dbname = ""
			elif self.auth in (DB_MONGODB,):
				self.dbtype = self.auth
				self.auth = None
				
		self._use_cache = use_cache		
		self._filter = filter
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
		self._numnodes = 0
		
		self._sent_result = None
		
		if self._cluster:
			nodes = self._cluster.get_nodes ()
			self._numnodes = len (nodes)
			if self._mapreduce:
				self._nodes = nodes
			else: # anyone of nodes
				self._nodes = [None]
		
	def _get_ident (self):
		cluster_name = self._cluster.get_name ()
		if cluster_name == "dbpool":
			_id = "%s/%s/%s" % (self.server, self.dbname, self.auth)
		else:
			_id = cluster_name
		_id += "/%s%s" % (
			",".join (map (lambda x: str (x), self._cached_request_args)),
			self._mapreduce and "/M" or ""
			)	
		return _id
				
	def _get_connection (self, id = None):
		if id is None: id = self._nodes.pop ()
		else: self._nodes = []
			
		if self.server:
			asyncon = self._cluster.get (self.server, self.dbname, self.auth, self.dbtype)		
		else:	
			asyncon = self._cluster.get (id)
		
		if self._cv is None:
			self._cv = asyncon._cv
		return asyncon
	
	def _request (self, method, params):
		self._cached_request_args = (method, params) # backup for retry
		if self._use_cache and rcache.the_rcache:
			self._cached_result = rcache.the_rcache.get (self._get_ident ())
			if self._cached_result is not None:
				return
		
		while self._avails ():
			asyncon = self._get_connection (None)			
			rs = Dispatcher (self._cv, asyncon.address, ident = not self._mapreduce and self._get_ident () or None, filterfunc = self._filter)
			req = request.Request (
				self.dbtype,
				self.server, 
				self.dbname,
				method, params, 
				self._callback and self._callback or rs.handle_result
			)
			self._requests [rs] = asyncon
			asyncon.execute (req)			
		trigger.wakeup ()
		return self


class ClusterDistCallCreator:
	def __init__ (self, cluster, logger):
		self.cluster = cluster
		self.logger = logger
	
	def __getattr__ (self, name):	
		return getattr (self.cluster, name)
		
	def Server (self, server = None, dbname = None, auth = None, dbtype = None, use_cache = True, mapreduce = False, filter = None, callback = None):
		# reqtype: xmlrpc, rpc2, json, jsonrpc, http
		#return ClusterDistCall (self.cluster, server, dbname, user, password, dbtype, use_cache, mapreduce, filter, callback, self.logger)
		return cluster_dist_call.Proxy (ClusterDistCall, self.cluster, server, dbname, auth, dbtype, use_cache, mapreduce, filter, callback, self.logger)
		
		