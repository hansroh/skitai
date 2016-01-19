from skitai import VERSION
import multiprocessing
from skitai.lib import pathtool, logger
from .rpc import cluster_manager, cluster_dist_call
from skitai.protocol.smtp import composer

PSYCOPG2_ENABLED = True
try: 
	import psycopg2
except ImportError: 
	PSYCOPG2_ENABLED = False
else:	
	from .dbi import cluster_manager as dcluster_manager, cluster_dist_call as dcluster_dist_call
	
from . import server_info
import json
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
	
try: 
	import _thread
except ImportError:
	import thread as _thread	
	
from skitai import lifetime


class _Method:
	def __init__(self, send, name):
		self.__send = send
		self.__name = name
		
	def __getattr__(self, name):
		return _Method(self.__send, "%s.%s" % (self.__name, name))
		
	def __call__(self, *args, **karg):		
		return self.__send(self.__name, args, karg)


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
			raise KeyError("server object `%s` is already exists")
		setattr (cls, name, obj)
	
	@classmethod
	def unregister (cls, name):
		del cls.objects [name]
		return delattr (cls, name)
		
	@classmethod
	def add_handler (cls, back, handler, *args, **karg):
		h = handler (cls, *args, **karg)
		if hasattr (cls, "httpserver"):
			cls.httpserver.install_handler (h, back)
		return h	
					
	@classmethod
	def add_cluster (cls, clustertype, clustername, clusterlist, ssl = 0):
		if PSYCOPG2_ENABLED and clustertype == "postgresql":
			cluster = dcluster_manager.ClusterManager (clustername, clusterlist, ssl, cls.logger.get ("server"))
			cls.clusters_for_distcall [clustername] = dcluster_dist_call.ClusterDistCallCreator (cluster, cls.logger.get ("server"))
		else:
			cluster = cluster_manager.ClusterManager (clustername, clusterlist, ssl, cls.logger.get ("server"))
			cls.clusters_for_distcall [clustername] = cluster_dist_call.ClusterDistCallCreator (cluster, cls.logger.get ("server"))
		cls.clusters [clustername] = cluster
			
	def __dir__ (self):
		return self.objects.keys ()
	
	def __str__ (self):
		return "was: Skitai WSGI Appliation Service"
	
	def __detect_cluster (self, clustername):
		try: 
			clustername, uri = clustername.split ("/", 1)
		except ValueError:
			clustername, uri = clustername, ""
		if clustername [0] == "@":
			clustername = clustername [1:]
		return clustername, "/" + uri
	
	def __getattr__ (self, name):
		return _Method(self._call, name)
	
	VALID_COMMANDS = ["ws", "get", "post", "rpc", "put", "upload", "delete", "options", "db"]
	def _call (self, method, args, karg):
		# was.db, 		was.get, 			was.post,			was.put, ...
		# was.db.lb, 	was.get.lb,		was.post.lb,	was.put.lb, ...
		# was.db.map,	was.get.map,	was.post.map,	was.put.map, ...
		
		uri = None
		if args:		uri = args [0]
		elif karg:	uri = karg.get ("uri", "")
		if not uri:	raise AssertionError ("missing param uri or cluster name")

		try: 
			command, fn = method.split (".")
		except ValueError: 
			command = method
			if uri [0] == "@": 
				fn = "lb"
			else:
				fn = (command == "db" and "db" or "rest")
				
		if command == "db":
			return getattr (self, "_d" + fn) (*args, **karg)
		if command not in self.VALID_COMMANDS:
			raise AttributeError ("WAS instance doesn't have '%s'" % method)			
		
		return getattr (self, "_" + fn) (command, *args, **karg)
	
	def _rest (self, method, uri, data = None, auth = None, headers = None, filter = None, encoding = None):
		#auth = (user, password)
		return self.clusters_for_distcall ["__socketpool__"].Server (uri, data, method, headers, auth, encoding, mapreduce = False, callback = filter)
			
	def _map (self, method, uri, data = None, auth = None, headers = None, filter = None, encoding = None):		
		clustername, uri = self.__detect_cluster (uri)		
		return self.clusters_for_distcall [clustername].Server (uri, data, method, headers, auth, encoding, mapreduce = True, callback = filter)
	
	def _lb (self, method, uri, data = None, auth = None, headers = None, filter = None, encoding = None):
		clustername, uri = self.__detect_cluster (uri)
		return self.clusters_for_distcall [clustername].Server (uri, data, method, headers, auth, encoding, mapreduce = False, callback = filter)
	
	def _ddb (self, server, dbname, user = "", password = "", dbtype = "postgresql", filter = None):
		return self.clusters_for_distcall ["__dbpool__"].Server (server, dbname, user, password, dbtype, mapreduce = False, callback = filter)
	
	def _dlb (self, clustername, filter = None):
		return self.clusters_for_distcall [clustername].Server (mapreduce = False, callback = filter)
	
	def _dmap (self, clustername, filter = None):
		return self.clusters_for_distcall [clustername].Server (mapreduce = True, callback = filter)
	
	def email (self, subject, snd, rcpt):
		return composer.Composer (subject, snd, rcpt)
		
	def tojson (self, obj):
		return json.dumps (obj)
	
	def toxml (self, obj):
		return xmlrpclib.dumps (obj, methodresponse = False, allow_none = True, encoding = "utf8")	
	
	def fromjson (self, obj):
		return json.loads (obj)
	
	def fromxml (self, obj, use_datetime=0):
		return xmlrpclib.loads (obj)	
											
	def status (self, flt = None, fancy = True):
		return server_info.make (self, flt, fancy)
	
	def restart (self, fast = 0):
		lifetime.shutdown (3, fast)
	
	def shutdown (self, fast = 0):
		lifetime.shutdown (0, fast)

	
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
		has_prefix = prefix in self.logger_factory
		if has_prefix:
			self.lock.release ()
			raise TypeError("%s is already used" % prefix)
								
		_logger = logger.multi_logger ()		
		_logger.add_logger (logger.rotate_logger (self.path, prefix, freq))
		
		self.logger_factory [prefix] = _logger		
		self.lock.release ()	
	
	def add_screen_logger (self):
		for prefix, _logger in list(self.logger_factory.items ()):
			_logger.add_logger (logger.screen_logger ())
		
	def get (self, prefix):
		return self.logger_factory [prefix]
			
	def trace (self, prefix, ident = ""):
		self.get (prefix).trace (ident)		
		
	def __call__ (self, prefix, msg, log_type = ""):		
		self.get (prefix).log (msg, log_type)
	
	def rotate (self):
		self.lock.acquire ()
		loggers = list(self.logger_factory.items ())
		self.lock.release ()
		
		for mlogger in loggers:
			for logger in mlogger.loggers:
				if hasattr (logger, "rotate"):
					logger.rotate ()
		
	def close (self):
		self.__application.close ()
		self.__request.close ()
		self.__server.close ()
