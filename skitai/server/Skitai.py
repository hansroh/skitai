#-------------------------------------------------------
# Basic Blade Server Architecture R2
# Hans Roh (hansroh@gmail.com)
# 2014.4.24 Python 2.7 port (from 2.4)
#-------------------------------------------------------

HTTPS = True
PSYCOPG = True
JSONRPBLIB = True

import sys, time, os, threading
from . import http_server, authorizer, appmanger, http_cookie, rcache
from skitai import lifetime
from warnings import warn

if os.name == "nt":	
	from . import schedule

try: from .handlers import jsonrpc_handler
except ImportError: JSONRPBLIB = False
	
try: from . import https_server
except ImportError:
	HTTPS = False

try: import psycopg2
except ImportError: 
	PSYCOPG = False	
else:			
	from skitai.dbapi import dbpool	
		
from .handlers import default_handler, ssgi_handler, \
	xmlrpc_handler, proxypass_handler, proxy_handler, \
	multipart_handler, resource_validate_handler, options_handler, \
	pingpong_handler
from .threads import threadlib, trigger
from skitai.lib import logger, confparse, pathtool, flock
from .rpc import cluster_dist_call, cachefs		
from skitai.client import socketpool
import socket
import signal
import multiprocessing
from . import webappservice

if PSYCOPG:
	from .dbi import cluster_dist_call as dcluster_dist_call

class Loader:
	def __init__ (self, config, logpath, varpath, debug = 0):
		self.config = config
		self.instance_name = os.path.split (config)[-1][:-5]
		self.logpath = logpath
		self.varpath = varpath
		self.debug = debug
		self.num_worker = 1
		self.wasc = webappservice.WAS
		self.ssl = False
		self.ctx = None
		self._exit_code = None
		self.config_logger (self.logpath)
		self.WAS_initialize ()
		self.configure ()
		self.WAS_finalize ()
	
	def configure (self):
		raise SystemExit("configure must be overided")
	
	def set_num_worker (self, num):	
		if os.name == "nt":
			num = 1
		self.num_worker = num
			
	def WAS_initialize (self):		
		self.wasc.register ("debug", self.debug)
		self.wasc.register ("plock", multiprocessing.RLock ())
		self.wasc.register ("clusters",  {})
		self.wasc.register ("clusters_for_distcall",  {})
		
	def WAS_finalize (self):
		self.wasc.register ("lock", threading.RLock ())
		self.wasc.register ("lifetime", lifetime)		
		
		socketfarm = socketpool.SocketPool (self.wasc.logger.get ("server"))
		self.wasc.clusters ["__socketpool__"] = socketfarm
		self.wasc.clusters_for_distcall ["__socketpool__"] = cluster_dist_call.ClusterDistCallCreator (socketfarm, self.wasc.logger.get ("server"))
		
		if PSYCOPG:
			dp = dbpool.DBPool (self.wasc.logger.get ("server"))
			self.wasc.clusters ["__dbpool__"] = dp
			self.wasc.clusters_for_distcall ["__dbpool__"] = dcluster_dist_call.ClusterDistCallCreator (dp, self.wasc.logger.get ("server"))
		
		if not hasattr (self.wasc, "threads"):
			for attr in ("map", "rpc", "rest", "wget", "lb", "db", "dlb", "dmap"):
				delattr (self.wasc, attr)
		
	def config_cachefs (self, cache_dir): 
		if cache_dir:
			self.wasc.register ("cachefs",  cachefs.CacheFileSystem (cache_dir))
	
	def config_rcache (self, maxobj = 2000):
		rcache.start_rcache (maxobj)
		self.wasc.register ("rcache", rcache.the_rcache)		
		
	def config_certification (self, certfile, keyfile = None, pass_phrase = None):
		if not HTTPS:
			return
		if not os.path.isfile (certfile):
			_certpath = os.path.join (os.path.split (os.path.split (self.config)[0])[0], "cert")
			certfile = os.path.join (_certpath, certfile)
			if keyfile:
				keyfile = os.path.join (_certpath, keyfile)
		self.ctx = https_server.init_context (certfile, keyfile, pass_phrase)		
		self.ssl = True
				
	def config_webserver (self, port, ip = "", name = "", ssl = False):
		# maybe be configured	at first.
		if ssl and not HTTPS:
			raise SystemError("Can't start SSL Web Server")
		
		if not name:
			name = self.instance_name
		http_server.http_server.SERVER_IDENT = name
		if ssl and self.ctx is None:
			raise ValueError("SSL ctx not setup")
		
		if ssl:
			server_class = https_server.https_server			
		else:	
			server_class = http_server.http_server
		
		if self.ssl:
			httpserver = server_class (ip and ip or "", port, self.ctx, self.wasc.logger.get ("server"), self.wasc.logger.get ("request"))	
		else:
			httpserver = server_class (ip and ip or "", port, self.wasc.logger.get ("server"), self.wasc.logger.get ("request"))	
		
		self.wasc.register ("httpserver", httpserver)
		
		#fork here 
		_exit_code = self.wasc.httpserver.fork_and_serve (self.num_worker)				
		if _exit_code is not None:
			self.handle_exit_code (_exit_code)
		
	def handle_exit_code (self, _exit_code):		
		self._exit_code = _exit_code				
		try:
			os.wait ()
		except OSError:	
			pass			
	
	def get_exit_code (self):	
		return self._exit_code
					
	def config_scheduler (self, conffile):
		if os.name == "nt":
			scheduler = schedule.Scheduler (self.wasc, conffile, self.wasc.logger.get ("server"))		
			self.wasc.register ("scheduler", scheduler)
	
	def config_logger (self, path):
		if path is not None:
			media = ["file"]
		else:
			media = ["screen"]	
		self.wasc.register ("logger", webappservice.Logger (media, path))
		
		if os.name != "nt":
			def hUSR1 (signum, frame):	
				self.wasc.logger.rotate ()
			signal.signal(signal.SIGUSR1, hUSR1)
		
	def config_authorizer (self, magic, password):
		auth = authorizer.Authorizer (self.instance_name, magic, password)		
		self.wasc.register ("authorizer", auth)
	
	def config_threads (self, numthreads = 0):
		if numthreads > 0:
			trigger.start_trigger ()
			queue = threadlib.request_queue2 ()
			tpool = threadlib.thread_pool (queue, numthreads, self.wasc.logger.get ("server"))
			self.wasc.register ("queue",  queue)
			self.wasc.register ("threads", tpool)
		
	def config_session (self, path, timeout, secret_key = ""):
		if not timeout: timeout = 1200
		if secret_key:
				http_cookie.Cookie.set_secret_key (secret_key)
		#self.wasc.register ("sessions", http_session.Sessions (path, timeout))
					
	def add_cluster (self, clustertype, clustername, clusterlist, ssl = 0):
		if ssl in ("1", "yes"): ssl = 1
		else: ssl = 0
		self.wasc.add_cluster (clustertype, clustername, clusterlist, ssl = ssl)
			
	def install_handler (self, routes = {}, proxy = False, static_max_age = 300, max_file_size = 0):		
		self.wasc.add_handler (1, pingpong_handler.Handler)
		clusters = self.wasc.clusters		
		if proxy:			
			self.wasc.add_handler (1, proxy_handler.Handler, clusters, self.wasc.cachefs)
		self.wasc.add_handler (1, proxypass_handler.Handler, clusters, self.wasc.cachefs)
		
		self.wasc.add_handler (1, options_handler.Handler)
		routes_directory = {}
		alternative_handlers = []
		self.wasc.add_handler (1, default_handler.Handler, routes_directory, static_max_age, alternative_handlers)
		
		apps = appmanger.ModuleManager(self.wasc)		
		self.wasc.register ("apps", apps)
		
		for line in routes:
			route, target = [x.strip () for x in line.split ("=", 1)]

			if target.startswith ("@"):
				if route [-1] == "/":
					route = route [:-1]
				clusters [target [1:].strip ()].set_route (route)				
			
			elif os.path.isdir (target):
				if route [-1] == "/":
					route = route [:-1]
				self.wasc.add_route (route, target)
				
			else:
				fullpath = os.path.split (target.strip())
				apps.add_module (route, os.sep.join (fullpath[:-1]), fullpath [-1])
			
		alternative_handlers.append (resource_validate_handler.Handler (self.wasc))
		alternative_handlers.append (multipart_handler.Handler (self.wasc, max_file_size))		
		alternative_handlers.append (xmlrpc_handler.Handler (self.wasc))
		if JSONRPBLIB:
			alternative_handlers.append (jsonrpc_handler.Handler (self.wasc))
		alternative_handlers.append (ssgi_handler.Handler (self.wasc))
		
	def run (self):
		if self._exit_code is not None: 
			return self._exit_code # master process
			
		try:
			try:
				lifetime.loop ()
			except:
				self.wasc.logger.trace ("server")					
		finally:
			self.close ()
		
		return None # worker process
		
	def close (self):
		for attr, obj in list(self.wasc.objects.items ()):
			if attr == "logger": continue
			try:
				self.wasc.logger ("server", "[info] clenaup %s" % attr)
				obj.cleanup ()				
				del obj
			except AttributeError:
				pass
			except:
				self.wasc.logger.trace ("server")
		
		if self.wasc.httpserver.worker_ident == "master":
			self.wasc.logger ("server", "[info] cleanup done, closing logger... bye")
			try:
				self.wasc.logger.close ()
				del self.wasc.logger
			except:
				pass

