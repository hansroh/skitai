#-------------------------------------------------------
# Basic Blade Server Architecture R2
# Hans Roh (hansroh@gmail.com)
# 2014.4.24 Python 2.7 port (from 2.4)
#-------------------------------------------------------

HTTPS = True
import sys, time, os, threading
from . import http_server
from skitai import lifetime
from warnings import warn
from . import https_server
from skitai import start_was
from collections import deque
from aquests.lib.athreads.fifo import await_fifo
from aquests.client import asynconnect
from aquests.client import socketpool
from aquests.lib.athreads import threadlib, trigger
from aquests.lib import logger, confparse, pathtool, flock
from aquests.dbapi import dbpool
from aquests.protocols.http import request_handler
from aquests.protocols import http2
from aquests.client import adns
if os.name == "nt":	
	from . import schedule			
from .handlers import proxy_handler, ipbl_handler, vhost_handler
from .rpc import cluster_dist_call, rcache
import socket
import signal
import multiprocessing
from . import wsgiappservice, cachefs
from .dbi import cluster_dist_call as dcluster_dist_call
import types
from skitai.server.handlers.websocket import servers as websocekts

class Loader:
	def __init__ (self, config = None, logpath = None, varpath = None, debug = 0):
		self.config = config
		self.instance_name = os.path.split (config)[-1][:-5]
		self.logpath = logpath
		self.varpath = varpath
		self.debug = debug
		self.num_worker = 1
		self.wasc = wsgiappservice.WAS
		self.ssl = False
		self.ctx = None
		self._exit_code = None
		self._fifo_switched = False
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
		self.wasc.workers = num
			
	def WAS_initialize (self):
		self.wasc.log_base_path = self.logpath and os.path.split (os.path.split (self.logpath)[0])[0]
		self.wasc.var_base_path = self.varpath and os.path.split (os.path.split (self.varpath)[0])[0]
		self.wasc.register ("debug", self.debug)
		self.wasc.register ("plock", multiprocessing.RLock ())
		self.wasc.register ("clusters",  {})
		self.wasc.register ("clusters_for_distcall",  {})
		self.wasc.register ("workers", 1)
		self.wasc.register ("cachefs", None)	
		websocekts.start_websocket (self.wasc)
		self.wasc.register ("websockets", websocekts.websocket_servers)
		self.switch_to_await_fifo ()
		
	def WAS_finalize (self):
		global the_was
		
		self.wasc.register ("lock", threading.RLock ())
		self.wasc.register ("lifetime", lifetime)		
		# internal connection should be http 1.1
		# because http2 single connection feature is useless on accessing internal resources
		# BUT we will use http2 when gRPC call, with just 1 stream per connection for speeding
		http2.MAX_HTTP2_CONCURRENT_STREAMS = 1
		request_handler.RequestHandler.FORCE_HTTP_11 = True
		adns.init (self.wasc.logger.get ("server"))
		start_was (self.wasc)
		
	def config_cachefs (self, cache_dir = None, memmax = 0, diskmax = 0):
		self.wasc.cachefs = cachefs.CacheFileSystem (cache_dir, memmax, diskmax)
		
		socketfarm = socketpool.SocketPool (self.wasc.logger.get ("server"))
		self.wasc.clusters ["__socketpool__"] = socketfarm
		self.wasc.clusters_for_distcall ["__socketpool__"] = cluster_dist_call.ClusterDistCallCreator (socketfarm, self.wasc.logger.get ("server"), self.wasc.cachefs)		
		
		dp = dbpool.DBPool (self.wasc.logger.get ("server"))
		self.wasc.clusters ["__dbpool__"] = dp
		self.wasc.clusters_for_distcall ["__dbpool__"] = dcluster_dist_call.ClusterDistCallCreator (dp, self.wasc.logger.get ("server"))
	
	def switch_to_await_fifo (self):
		if self._fifo_switched: return
		asynconnect.AsynConnect.fifo_class = await_fifo
		asynconnect.AsynSSLConnect.fifo_class = await_fifo
		http_server.http_channel.fifo_class = await_fifo
		https_server.https_channel.fifo_class = await_fifo
		self._fifo_switched = True
			
	def config_rcache (self, maxobj = 1000):
		rcache.start_rcache (maxobj)
		self.wasc.register ("rcache", rcache.the_rcache)
		
	def config_certification (self, certfile, keyfile = None, pass_phrase = None):
		if not HTTPS:
			return
		self.ctx = https_server.init_context (certfile, keyfile, pass_phrase)
		self.ssl = True
				
	def config_webserver (self, port, ip = "", name = "", ssl = False, keep_alive = 10, response_timeout = 10):
		# maybe be configured	at first.
		if ssl and not HTTPS:
			raise SystemError("Can't start SSL Web Server")
		
		if not name:
			name = self.instance_name		
		http_server.configure (name, response_timeout, keep_alive)
				
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
	
	def config_logger (self, path, media = None):
		if not media:
			if path is not None:
				media = ["file"]
			else:
				media = ["screen"]
		
		self.wasc.register ("logger", wsgiappservice.Logger (media, path))
		if os.name != "nt" and path:
			def hUSR1 (signum, frame):	
				self.wasc.logger.rotate ()
			signal.signal(signal.SIGUSR1, hUSR1)
	
	def config_threads (self, numthreads = 0):
		if numthreads > 0:
			trigger.start_trigger (self.wasc.logger.get ("server"))
			queue = threadlib.request_queue2 ()
			tpool = threadlib.thread_pool (queue, numthreads, self.wasc.logger.get ("server"))
			self.wasc.register ("queue",  queue)
			self.wasc.register ("threads", tpool)
			self.wasc.numthreads = numthreads
					
	def add_cluster (self, clustertype, clustername, clusterlist, ssl = 0, access = None):
		if clustertype and clustertype [0] == "*":
			clustertype = clustertype [1:]
		ssl = 0
		if ssl in (1, True, "1", "yes") or clustertype in ("https", "wss", "grpcs", "rpcs"):
			ssl = 1
		if type (clusterlist)	is str:
			clusterlist = [clusterlist]		
		self.wasc.add_cluster (clustertype, clustername, clusterlist, ssl = ssl, access = access)
	
	def install_handler_with_tuple (self, routes):
		if type (routes) is list:
			routes = {'default': routes}
		sroutes = []
		for domain in routes:
			sroutes.append ("@%s" % domain)
			for route, entity, pref in routes [domain]:				
				appname = None
				if type (entity) is tuple:
					entity, appname = entity				
				if type (entity) is not str:
					entity = os.path.join (os.getcwd (), sys.argv [0])
				if entity.endswith (".py") or entity.endswith (".pyc"):
					entity = os.path.join (os.getcwd (), entity) [:-3]
					if entity [-1] == ".":
						entity = entity [:-1]
				sroutes.append (("%s=%s%s" % (route, entity, appname and ":" + appname or ""), pref))
		return sroutes
			
	def install_handler (self, 
			routes = [], 
			proxy = False, 
			static_max_ages = None, 
			blacklist_dir = None, 
			unsecure_https = False, 
			enable_apigateway = False,
			apigateway_authenticate = False, 
			apigateway_realm = "API Gateway",
			apigateway_secret_key = None
		):
		
		if routes:
			if type (routes) is dict:
				routes = self.install_handler_with_tuple (routes)
			else:
				if type (routes) is not list:
					routes = [routes]
				if type (routes [0]) is tuple:
					routes = self.install_handler_with_tuple (routes)

		if blacklist_dir:
			self.wasc.add_handler (0, ipbl_handler.Handler, blacklist_dir)
		if proxy:			
			self.wasc.add_handler (1, proxy_handler.Handler, self.wasc.clusters, self.wasc.cachefs, unsecure_https)		
		
		vh = self.wasc.add_handler (
			1, vhost_handler.Handler, 
			self.wasc.clusters, self.wasc.cachefs, 
			static_max_ages, 
			enable_apigateway, apigateway_authenticate, apigateway_realm, apigateway_secret_key
		)
		
		current_rule = "default"
		for line in routes:			
			config = None
			if type (line) is tuple:
				line, pref = line
			line = line.strip ()
			if line.startswith (";") or line.startswith ("#"):
				continue
			elif line.startswith ("/"):
				reverse_proxing = vh.add_route (current_rule, line, pref)					
			elif line:
				if line [0] == "@":
					line = line [1:].strip ()					
				current_rule = line
			
	def run (self, timeout = 30):
		if self._exit_code is not None: 	
			self.close ()		
			return self._exit_code # master process
			
		try:
			try:
				lifetime.loop (timeout)
			except:
				self.wasc.logger.trace ("server")					
		finally:
			self.close ()
		
		return None # worker process
		
	def close (self):
		for attr, obj in list(self.wasc.objects.items ()):
			if attr == "logger": 
				continue
			
			if attr == "clusters":
				self.wasc.logger ("server", "[info] clenaup %s" % attr)
				for name, cluster in obj.items ():
					self.wasc.logger ("server", "[info] ...clenaup %s" % name)
					cluster.cleanup ()
				continue	
					
			try:
				self.wasc.logger ("server", "[info] clenaup %s" % attr)
				obj.cleanup ()
				del obj
			except AttributeError:
				pass
			except:
				self.wasc.logger.trace ("server")
		
		if os.name == "nt" or self.wasc.httpserver.worker_ident == "master":
			self.wasc.logger ("server", "[info] cleanup done, closing logger... bye")
			try:
				self.wasc.logger.close ()
				del self.wasc.logger
			except:
				pass

