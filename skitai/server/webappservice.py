from skitai import VERSION
import multiprocessing
from skitai.lib import pathtool, logger
from rpc import cluster_manager, cluster_dist_call
from dbi import cluster_manager as dcluster_manager, cluster_dist_call as dcluster_dist_call
from handlers import default_handler
import server_info


class WAS:
	version = VERSION
	objects = {}
	#----------------------------------------------------
	# application friendly methods
	#----------------------------------------------------		
	@classmethod
	def register (cls, name, obj):
		cls.objects [name] = obj
		if hasattr (cls, name):
			raise KeyError, "server object `%s` is already exists"
		setattr (cls, name, obj)
	
	@classmethod
	def unregister (cls, name):
		del cls.objects [name]
		return delattr (cls, name)
	
	@classmethod
	def add_route (cls, v, r):
		for h in cls.httpserver.handlers:
			if isinstance (h, default_handler.Handler):
				h.add_route (v, r)
		
	@classmethod
	def add_handler (cls, back, handler, *args, **karg):
		h = handler (cls, *args, **karg)
		if hasattr (cls, "httpserver"):
			cls.httpserver.install_handler (h, back)
					
	@classmethod
	def add_cluster (cls, clustertype, clustername, clusterlist, ssl = 0):
		if clustertype == "postgresql":
			cluster = dcluster_manager.ClusterManager (clustername, clusterlist, ssl, cls.logger.get ("server"))
			cls.clusters_for_distcall [clustername] = dcluster_dist_call.ClusterDistCallCreator (cluster, cls.logger.get ("server"))
		else:
			cluster = cluster_manager.ClusterManager (clustername, clusterlist, ssl, cls.logger.get ("server"))
			cls.clusters_for_distcall [clustername] = cluster_dist_call.ClusterDistCallCreator (cluster, cls.logger.get ("server"))
		cls.clusters [clustername] = cluster
	
	def map (self, clustername, req_type, params = None, login = None, encoding = None, multipart = False, filter = None):
		return self.clusters_for_distcall [clustername].Server (req_type, params, login, encoding, multipart = multipart, mapreduce = True, callback = filter)
	
	def lb (self, clustername, req_type, params = None, login = None, encoding = None, multipart = False, filter = None):
		return self.clusters_for_distcall [clustername].Server (req_type, params, login, encoding, multipart = multipart, mapreduce = False, callback = filter)
		
	def wget (self, uri, params = None, login = None, encoding = None, multipart = False, filter = None):
		return self.lb ("__socketpool__", uri, params, login, encoding, multipart, filter)
		
	def rpc (self, *args, **karg):
		return self.wget (*args, **karg)
	
	def db (self, server, dbname, user, password, dbtype = "postgresql", filter = None):
		return self.clusters_for_distcall ["__dbpool__"].Server (server, dbname, user, password, dbtype, mapreduce = False, callback = filter)
	
	def dlb (self, clustername, filter = None):
		return self.clusters_for_distcall [clustername].Server (mapreduce = False, callback = filter)
	
	def dmap (self, clustername, filter = None):
		return self.clusters_for_distcall [clustername].Server (mapreduce = True, callback = filter)
				
	def status (self, flt = None, fancy = True):
		#reload (server_info)
		return server_info.make (self, flt, fancy)
		

class Logger:
	def __init__ (self, media, path):
		self.media = media
		self.path = path
		if self.path: pathtool.mkdir (path)
		self.logger_factory = {}
		self.lock = multiprocessing.Lock ()
			
		self.make_logger ("server", "monthly")
		self.make_logger ("request", "daily")
		self.make_logger ("app", "daily")

	def make_logger (self, prefix, freq = "daily"):
		self.lock.acquire ()
		has_prefix = self.logger_factory.has_key (prefix)
		if has_prefix:
			self.lock.release ()
			raise TypeError, "%s is already used" % prefix
								
		_logger = logger.multi_logger ()		
		_logger.add_logger (logger.rotate_logger (self.path, prefix, freq))
		
		self.logger_factory [prefix] = _logger		
		self.lock.release ()	
	
	def add_screen_logger (self):
		for prefix, _logger in self.logger_factory.items ():
			_logger.add_logger (logger.screen_logger ())
		
	def get (self, prefix):
		return self.logger_factory [prefix]
			
	def trace (self, prefix, ident = ""):
		self.get (prefix).trace (ident)		
		
	def __call__ (self, prefix, msg, log_type = ""):		
		self.get (prefix).log (msg, log_type)
	
	def rotate (self):
		self.lock.acquire ()
		loggers = self.logger_factory.items ()
		self.lock.release ()
		
		for mlogger in loggers:
			for logger in mlogger.loggers:
				if hasattr (logger, "rotate"):
					logger.rotate ()
		
	def close (self):
		self.__application.close ()
		self.__request.close ()
		self.__server.close ()
