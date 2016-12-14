import threading
from skitai.client import asynconnect
import time
import re
import copy
import random
from operator import itemgetter

class ClusterManager:
	object_timeout = 1200
	maintern_interval = 30
	
	def __init__ (self, name, cluster, ssl = 0, logger = None):
		self.logger = logger
		self.lock = threading.RLock ()
		self._name = name
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
			
	def is_ssl_cluster (self):
		return self._use_ssl
		
	def set_ssl (self, flag):
		self._use_ssl = flag
		if flag:
			self._conn_class = asynconnect.AsynSSLConnect	
		else:
			self._conn_class = asynconnect.AsynConnect
	
	def status (self):
		info = {}
		cluster = {}
		self.lock.acquire ()
		try:
			try:	
				for node in self._cluster:
					_node = copy.copy (self._cluster [node])
					_node ["numactives"] = len ([x for x in _node ["connection"] if x.isactive ()])
					_node ["numconnected"] = len ([x for x in _node ["connection"] if x.isconnected ()])
					
					conns = []
					for asyncon in _node ["connection"]:
						conn = {
								"connected": asyncon.isconnected (), 
								"isactive": asyncon.isactive (), 
								"request_count": asyncon.get_request_count (),
								"event_time": time.asctime (time.localtime (asyncon.event_time)),
								"zombie_timeout": asyncon.zombie_timeout,	
							}
						if hasattr (asyncon, "get_history"):
							conn ["history"] = asyncon.get_history ()								
						conns.append (conn)
								
					_node ["connection"] = conns
					cluster [str (node)] = _node
				info ["cluster"] = cluster
				
				actives = len ([x for x in self._close_desires if x.isactive ()])
				connecteds = len ([x for x in self._close_desires if x.isconnected ()])
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
				for node in list(self._cluster.keys ()):
					self._cluster [node]["stoped"] = True
					for asyncon in self._cluster [node]["connection"]:
						asyncon.disconnect ()
			finally:	
				self.lock.release ()
		except:
			self.logger.trace ()	
	
	def get_nodes (self):
		nodes = []
		self.lock.acquire ()
		try:
			try:
				nodes = [k for k, v in list(self._cluster.items ()) if not v ["stoped"]]
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
			if not self._use_ssl:
				server	= (member, 80)			
			else:	
				server	= (member, 443)
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
		exists = node in self._cluster
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
				if node in self._cluster:
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
				if node in self._cluster:
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
	
	def maintern (self):
		try:
			# close unused sockets
			for _node in list(self._cluster.values ()):
				survived = []
				for asyncon in _node ["connection"]:
					if hasattr (asyncon, "maintern"):
						continue
																		
					if not asyncon.maintern (self.object_timeout):					
						# not deletable
						survived.append (asyncon)
														
				if len (survived) == 0:
					# at least 1 must be survived for duplicating
					_node ["connection"] = _node ["connection"][:1]
				elif len (_node ["connection"]) != len (survived):
					_node ["connection"] = survived
			
			# checking dead nodes
			if self._havedeadnode:
				for node in [k for k, v in list(self._cluster.items ()) if v ["check"] is not None and not v ["stoped"]]:
					if time.time () > self._cluster [node]["check"]:
						self._cluster [node]["check"] = None
			
			# closing removed mode's sockets					
			if self._close_desires:
				cannot_closes = []
				for asyncon in self._close_desires:
					if asyncon.isactive ():
						cannot_closes.append (asyncon)
					else:						
						asyncon.disconnect ()
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
				if time.time () - self._last_maintern > self.maintern_interval:
					self.maintern ()
					
				if specific:
					nodes = [specific]
				
				elif index != -1:
					try:
						nodes = [self._clusterlist [index]]
					except IndexError:
						nodes = [self._clusterlist [-1]]
						
				else:	
					nodes = [k for k, v in list(self._cluster.items ()) if v ["check"] is None and not v ["stoped"]]
					self._havedeadnode = len (self._cluster) - len (nodes)
					if not nodes:
						#assume all live...
						nodes = [k for k, v in list(self._cluster.items ()) if not v ["stoped"]]
										
				cluster = []
				for node in nodes:
					avails = [x for x in self._cluster [node]["connection"] if not x.isactive ()]
					if not avails:
						continue
					
					weight = self._cluster [node]["weight"]
					actives = weight - len (avails)
					
					if actives == 0:
						capability = 1.0
					else:
						capability = 1.0 - (actives / float (weight))

					cluster.append ((avails [0], capability, weight))
				
				if cluster:
					random.shuffle (cluster) # load balancing between same weighted members
					cluster.sort (key = itemgetter(1, 2), reverse = True)
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
	
	def sortfunc (self, a, b):
		r = b [1] - a [1]
		if r != 0: return r
		return b [2] - a [2]		
