import threading
from skitai.server.threads import socket_map
from skitai.client import asynconnect, adns
import time
import urlparse
import re
import copy
import random

class ClusterManager:
	object_timeout = 1200
	
	def __init__ (self, name, cluster, ssl = 0, logger = None):
		self.logger = logger
		self.lock = threading.RLock ()
		self._name = name
		self._route_rx = None
		self._route = None
		self._routelen = 0
				
		self.set_ssl (ssl)
		
		self._havedeadnode = 0
		self._numget = 0
		self._nummget = 0
		self._clusterlist = []
		self._cluster = {}	
		self._last_maintern = time.time ()
		self._close_desires = []
		 
		if cluster:
			self.create_pool (cluster)
	
	def __len__ (self):
		return len (self._cluster)
		
	def get_name (self):
		return self._name
		
	def set_route (self, route):
		self._route = route
		self._routelen = len (route)
		self._route_rx = re.compile ("%s(?P<rti>[0-9]*)" % route, re.I)
			
	def is_ssl_cluster (self):
		return self._use_ssl
		
	def set_ssl (self, flag):
		self._use_ssl = flag
		if flag:
			self._conn_class = asynconnect.AsynSSLConnect	
		else:
			self._conn_class = asynconnect.AsynConnect
	
	def match (self, request):
		if not (self._route_rx):
			return False	# used only rpc-call
		uri = request.uri
		if self._route_rx:			
			match = self._route_rx.match (uri)
			if not match: return False		
		return True
	
	def get_path_length (self):
		return self._routelen
			
	def get_route_index (self, request):
		if not self._route_rx:
			return ""
		return self._route_rx.match (request.uri).group ("rti")
	
	def status (self):
		info = {}
		cluster = {}
		self.lock.acquire ()
		try:
			try:	
				for node in self._cluster:
					_node = copy.copy (self._cluster [node])
					_node ["numactives"] = len (filter (lambda x: x.isactive (), _node ["connection"]))
					_node ["numconnected"] = len (filter (lambda x: x.isconnected (), _node ["connection"]))
					
					conns = []
					for asyncon in _node ["connection"]:
						conns.append (
							{
								"connected": asyncon.isconnected (), 
								"isactive": asyncon.isactive (), 
								"request_count": asyncon.get_request_count (),
								"event_time": time.asctime (time.localtime (asyncon.event_time)),
								"zombie_timeout": asyncon.zombie_timeout,	
							}
						)
					_node ["connection"] = conns
					cluster ["%s:%d" % node] = _node				
				info ["cluster"] = cluster
				
				actives = len (filter (lambda x: x.isactive (), self._close_desires))
				connecteds = len (filter (lambda x: x.isconnected (), self._close_desires))
				info ["close_pending"] = "%d (active: %d, connected: %d)" % (len (self._close_desires), actives, connecteds)
				info ["numget"] = self._numget
				info ["nummget"] = self._nummget
				info ["ssl"] = self.is_ssl_cluster ()				
				
			finally:
				self.lock.release ()
		except:
			self.logger.trace ()
		
		return info
		
	def cleanup (self):
		self.lock.acquire ()
		try:
			try:
				for node in self._cluster.keys ():
					self._cluster [node]["stoped"] = True
					for asyncon in self._cluster [node]["connection"]:
						asyncon.close_socket ()
			finally:	
				self.lock.release ()
		except:
			self.logger.trace ()	
	
	def get_nodes (self):
		nodes = []
		self.lock.acquire ()
		try:
			try:
				nodes = [k for k, v in self._cluster.items () if not v ["stoped"]]
			finally:	
				self.lock.release ()
		except:
			self.logger.trace ()					
		return nodes
		
	def get_cluster (self):
		return self._cluster
	
	def create_asyncon (self, member):
		try: 
			host, port = member.split (":", 1)
			server = (host, int (port))
		except ValueError: 
			server	= (member, 80)			
		asyncon = self._conn_class (server, self.lock, self.logger)
		return server, asyncon # nodeid, asyncon
		
	def add_node (self, member):
		try:				
			member, weight = member.split (" ", 1)
			weight = int (weight)
		except ValueError:
			weight = 1
		
		node, asyncon = self.create_asyncon (member)
		
		self.lock.acquire ()
		exists = self._cluster.has_key (node)
		self.lock.release ()		
		if exists: 
			self._cluster [node]["weight"] = weight
			return
		
		_node = {"check": None, "connection": [], "weight": weight, "deadcount": 0, "stoped": False, "deadtotal": 0}
		_node ["connection"] = [asyncon]
					
		self.lock.acquire ()		
		self._cluster [node] = _node
		self._clusterlist.append (node)
		self.lock.release ()
		
	def remove_node (self, member):
		host, port = member.split (":", 1)
		node = (host, int (port))
		self.lock.acquire ()
		try:
			try:	
				if self._cluster.has_key (node):
					self._close_desires += self._cluster [node]["connection"]
					del self._cluster [node]
					del self._clusterlist [self._clusterlist.index (node)]					
			finally:		
				self.lock.release ()
		except:
			self.logger.trace ()		
	
	def switch_node (self, member, stop = False):
		host, port = member.split (":", 1)
		node = (host, int (port))
		self.lock.acquire ()
		try:
			try:
				if self._cluster.has_key (node):
					self._cluster [node]["stoped"] = stop
					if stop is False:
						self._cluster [node]["deadcount"] = 0
						self._cluster [node]["check"] = None
										
			finally:		
				self.lock.release ()
		except:
			self.logger.trace ()
			
	def create_pool (self, cluster):
		for member in cluster:
			self.add_node (member)
	
	def report (self, asyncon, well_functioning):
		node = asyncon.address
		self.lock.acquire ()
		try:
			try:
				cluster = self._cluster
				if not well_functioning:
					if cluster [node]["deadcount"] < 10:
						recheck = 60
					else:
						recheck = 60 * 10
					cluster [node]["check"] = time.time () + recheck
					cluster [node]["deadcount"] += 1
					cluster [node]["deadtotal"] += 1
					
				else:
					cluster [node]["deadcount"] = 0
					cluster [node]["check"] = None
					
			finally:	
				self.lock.release ()
				
		except:
			self.logger.trace ()		
	
	def sortfunc (self, a, b):
		r = cmp (b [1], a [1])
		if r != 0: return r
		return cmp (b [2], a [2])
	
	def maintern (self):
		try:
			# close unused sockets
			for _node in self._cluster.values ():
				survived = []
				for asyncon in _node ["connection"]:
					if hasattr (asyncon, "maintern"):
						asyncon.maintern ()													
					if not asyncon.is_deletable (self.object_timeout):
						survived.append (asyncon)
														
				if len (survived) == 0:
					# at least 1 must be survived ro duplicate
					_node ["connection"] = _node ["connection"][:1]
				elif len (_node ["connection"]) != len (survived):
					_node ["connection"] = survived
			
			# checking dead nodes
			if self._havedeadnode:
				for node in [k for k, v in self._cluster.items () if v ["check"] is not None and not v ["stoped"]]:
					if time.time () > self._cluster [node]["check"]:
						self._cluster [node]["check"] = None
			
			# closing removed mode's sockets					
			if self._close_desires:
				cannot_closes = []
				for asyncon in self._close_desires:
					if asyncon.isactive ():
						cannot_closes.append (asyncon)
					else:
						asyncon.close_socket ()
						del asyncon
				self._close_desires = cannot_closes
				
		except:
			self.logger.trace ()
				
		self._last_maintern = time.time ()
			
	def get (self, specific = None, index = -1):
		asyncon = None
		self.lock.acquire ()
		try:
			try:
				self._numget += 1
				if time.time () - self._last_maintern > 60:
					self.maintern ()
					
				if specific:
					nodes = [specific]
				
				elif index != -1:
					try:
						nodes = [self._clusterlist [index]]
					except IndexError:
						nodes = [self._clusterlist [-1]]
						
				else:	
					nodes = [k for k, v in self._cluster.items () if v ["check"] is None and not v ["stoped"]]
					self._havedeadnode = len (self._cluster) - len (nodes)
					if not nodes:
						#assume all live...
						nodes = [k for k, v in self._cluster.items () if not v ["stoped"]]
										
				cluster = []
				for node in nodes:
					avails = filter (lambda x: not x.isactive (), self._cluster [node]["connection"])
					if not avails: 
						continue
					weight = self._cluster [node]["weight"]
					cluster.append ((avails [0], len (avails) / float (weight), weight))
				
				if cluster:
					cluster.sort (self.sortfunc)
					asyncon = cluster [0][0]					
				else:
					t = [(len (self._cluster [node]["connection"]), node) for node in nodes]
					t.sort ()
					node = t [0][1]
					asyncon = self._cluster [node]["connection"][0].duplicate ()		
					self._cluster [node]["connection"].append (asyncon)
									
				asyncon.set_active (True, nolock = True)							
				
			finally:
				self.lock.release ()	
		
		except:
			self.logger.trace ()
					
		return asyncon

