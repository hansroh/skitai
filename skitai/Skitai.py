#-------------------------------------------------------
# Basic Blade Server Architecture R2
# Hans Roh (hansroh@gmail.com)
# 2014.4.24 Python 2.7 port (from 2.4)
#-------------------------------------------------------

HTTPS = True
import sys, time, os, threading
from .backbone import http_server
from skitai import lifetime
from warnings import warn
from .backbone import https_server
from skitai import start_was
from collections import deque
from aquests.athreads.fifo import await_fifo
from aquests.client import asynconnect
from aquests.client import socketpool
from aquests.athreads import threadlib, trigger
from rs4 import logger, confparse, pathtool
from aquests.dbapi import dbpool
from aquests.protocols.http import request_handler
from aquests.protocols import http2
from aquests.client import adns
from aquests.protocols import dns
if os.name == "nt":
	from rs4.psutil import schedule # cron like scheduler
from rs4.psutil import kill
from .handlers import proxy_handler, ipbl_handler, vhost_handler, forward_handler
import socket
import signal
import multiprocessing
from . import wsgiappservice
from .backbone import http_response
from .corequest import cachefs
from .corequest.httpbase import task, rcache
from .corequest.httpbase import cluster_manager as rcluster_manager
from .corequest.dbi import cluster_manager as dcluster_manager
from .corequest.dbi import task as dtask
import types
from .handlers.websocket import servers as websocekts
from .wastuff import selective_logger, triple_logger
from .corequest.pth import executors

class Loader:
	def __init__ (self, config = None, logpath = None, varpath = None, wasc = None, debug = 0):
		self.config = config
		self.instance_name = os.path.split (config)[-1][:-5]
		self.logpath = logpath
		self.varpath = varpath
		self.debug = debug
		self.num_worker = 1
		self.wasc = wasc or wsgiappservice.WAS
		self.ssl = False
		self.ctx = None
		self._exit_code = None
		self.wasc_kargs = {}
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
		self.wasc.log_base_path = self.logpath
		self.wasc.var_base_path = self.varpath
		self.wasc.register ("debug", self.debug)
		self.wasc.register ("clusters",  {})
		self.wasc.register ("clusters_for_distcall",  {})
		self.wasc.register ("workers", 1)
		self.wasc.register ("cachefs", None)
		websocekts.start_websocket (self.wasc)
		self.wasc.register ("websockets", websocekts.websocket_servers)
		self.switch_to_await_fifo ()

	def set_model_keys (self, keys):
		self.wasc._luwatcher.add (keys)

	def get_app_by_name (self, name):
		for h in self.wasc.httpserver.handlers:
			if isinstance (h, vhost_handler.Handler):
				for vhost in h.sites.values ():
					if name in vhost.apps.modnames:
						return vhost.apps.modnames [name].get_callable ()

	def app_cycle (self, func):
		for h in self.wasc.httpserver.handlers:
			if isinstance (h, vhost_handler.Handler):
				for vhost in h.sites.values ():
					for apphs in vhost.apps.modules.values ():
						for apph in apphs:
							getattr (apph, func) ()

	def WAS_finalize (self):
		global the_was

		self.wasc.register ("lifetime", lifetime)
		# internal connection should be http 1.1
		# because http2 single connection feature is useless on accessing internal resources
		# BUT we will use http2 when gRPC call, with just 1 stream per connection for speeding
		http2.MAX_HTTP2_CONCURRENT_STREAMS = 1
		request_handler.RequestHandler.FORCE_HTTP_11 = True
		self.app_cycle ('mounted')
		start_was (self.wasc, **self.wasc_kargs)

	def config_wasc (self, **kargs):
		self.wasc_kargs = kargs

	def config_dns (self, prefer_protocol = "tcp"):
		adns.init (self.wasc.logger.get ("server"), prefer_protocol = prefer_protocol)
		lifetime.maintern.sched (4.1, dns.pool.maintern)

	def config_executors (self, workers, zombie_timeout, process_start = None):
		if process_start:
			from multiprocessing import set_start_method
			try: set_start_method (process_start, force = True)
			except RuntimeError: pass
		self.wasc.register ("executors", executors.Executors (workers, zombie_timeout, self.wasc.logger.get ("server")))

	def config_cachefs (self, cache_dir = None, memmax = 0, diskmax = 0):
		self.wasc.cachefs = cachefs.CacheFileSystem (cache_dir, memmax, diskmax)

		socketfarm = socketpool.SocketPool (self.wasc.logger.get ("server"))
		self.wasc.clusters ["__socketpool__"] = socketfarm
		self.wasc.clusters_for_distcall ["__socketpool__"] = task.TaskCreator (socketfarm, self.wasc.logger.get ("server"), self.wasc.cachefs)

		dp = dbpool.DBPool (self.wasc.logger.get ("server"))
		self.wasc.clusters ["__dbpool__"] = dp
		self.wasc.clusters_for_distcall ["__dbpool__"] = dtask.TaskCreator (dp, self.wasc.logger.get ("server"))

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

	def config_forward_server (self, ip = "", port = 80, forward_to = 443):
		forward_server = http_server.http_server (ip or "", port, self.wasc.logger.get ("server"), self.wasc.logger.get ("request"))
		forward_server.zombie_timeout = 2
		forward_server.install_handler (forward_handler.Handler (self.wasc, forward_to))
		self.wasc.register ("forwardserver", forward_server)

	def config_webserver (self, port, ip = "", name = "", ssl = False, keep_alive = 10, network_timeout = 10, single_domain = None, thunks = [], quic = None, backlog = 100, multi_threaded = False, max_upload_size = 256000000):
		# maybe be configured	at first.
		if ssl and not HTTPS:
			raise SystemError("Can't start SSL Web Server")

		if not name:
			name = self.instance_name
		http_server.configure (name, network_timeout, keep_alive, multi_threaded, max_upload_size)

		if ssl and self.ctx is None:
			raise ValueError("SSL ctx not setup")
		if ssl:
			server_class = https_server.https_server
		else:
			server_class = http_server.http_server

		if self.ssl:
			httpserver = server_class (ip or "", port, self.ctx, quic, self.wasc.logger.get ("server"), self.wasc.logger.get ("request"))
		else:
			httpserver = server_class (ip or "", port, self.wasc.logger.get ("server"), self.wasc.logger.get ("request"))
		single_domain and httpserver.set_single_domain (single_domain)
		self.wasc.register ("httpserver", httpserver)
		# starting jobs before forking
		for thunk in thunks:
			thunk ()

		self.wasc.httpserver.serve (hasattr (self.wasc, "forwardserver") and self.wasc.forwardserver or None, backlog)
		self.fork ()

	def fork (self):
		#fork here
		_exit_code = self.wasc.httpserver.fork (self.num_worker)
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

	def config_logger (self, path, media = None, log_off = [], file_loggings = None):
		if not media:
			if path is not None:
				media = ["file"]
			else:
				media = ["screen"]

		http_response.http_response.log_or_not = selective_logger.SelectiveLogger (log_off)
		self.wasc.register ("logger", triple_logger.Logger (media, path, file_loggings))

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

	def config_backends (self, backend_keep_alive, object_timeout, maintern_interval):
		rcluster_manager.ClusterManager.backend_keep_alive = backend_keep_alive
		rcluster_manager.ClusterManager.object_timeout = object_timeout
		rcluster_manager.ClusterManager.maintern_interval = maintern_interval

		dcluster_manager.ClusterManager.backend_keep_alive = backend_keep_alive
		dcluster_manager.ClusterManager.object_timeout = object_timeout
		dcluster_manager.ClusterManager.maintern_interval = maintern_interval

	def add_cluster (self, clustertype, clustername, clusterlist, ssl = 0, access = None, max_conns = 100):
		try:
			self.wasc.add_cluster (clustertype, clustername, clusterlist, ssl = ssl, access = access, max_conns = max_conns)
		except:
			self.wasc.logger.trace ("server")

	def install_handler_with_tuple (self, routes):
		if type (routes) is list:
			routes = {'default': routes}
		sroutes = []
		for domain in sorted (routes.keys ()): # must sort for lueatcher reservation
			sroutes.append ("@%s" % domain)
			for route, entity, pref, name in routes [domain]:
				appname = None
				if type (entity) is tuple:
					entity, appname = entity
				if entity.endswith (".py") or entity.endswith (".pyc"):
					entity = os.path.join (os.getcwd (), entity) [:-3]
					if entity [-1] == ".":
						entity = entity [:-1]
				sroutes.append (("%s=%s%s" % (route, entity, appname and ":" + appname or ""), pref, name))
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
				line, pref, name = line
			line = line.strip ()
			if line.startswith (";") or line.startswith ("#"):
				continue
			elif line.startswith ("/"):
				reverse_proxing = vh.add_route (current_rule, line, pref, name)
			elif line:
				if line [0] == "@":
					line = line [1:].strip ()
				current_rule = line

	def run (self, timeout = 30):
		if self._exit_code is not None:
			self.close ()
			return self._exit_code # win43 master process

		try:
			try:
				if "---memtrack" in sys.argv:
					self.wasc.logger ("server", "memory tracking enabled", "debug")
					lifetime.enable_memory_track ()
				if "---profile" in sys.argv:
					import cProfile
					self.wasc.logger ("server", "profiling enabled", "debug")
					cProfile.runctx ("lifetime.loop (timeout)", globals (), locals (), "profile.out")
				else:
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
				self.wasc.logger ("server", "[info] cleanup %s" % attr)
				for name, cluster in obj.items ():
					cluster.cleanup ()
				continue

			if hasattr (obj, "cleanup"):
				try:
					self.wasc.logger ("server", "[info] cleanup %s" % attr)
					obj.cleanup ()
					del obj
				except:
					self.wasc.logger.trace ("server")

		self.app_cycle ('umounted')

		if os.name == "nt" or self.wasc.httpserver.worker_ident == "master":
			self.wasc.logger ("server", "[info] cleanup done, closing logger... bye")
			try:
				self.wasc.logger.close ()
				del self.wasc.logger
			except:
				pass

		# finally, kill child processes
		kill.child_processes_gracefully ()
