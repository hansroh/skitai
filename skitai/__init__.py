# 2014. 12. 9 by Hans Roh hansroh@gmail.com

__version__ = "0.26.4.1"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  __version__.split (".")))
NAME = "Skitai/%s.%s" % version_info [:2]

import threading
import sys, os
import h2
from aquests.lib.attrdict import AttrDict
from importlib import machinery

WEBSOCKET_SIMPLE = 1
WEBSOCKET_DEDICATE_THREADSAFE = 4
WEBSOCKET_GROUPCHAT = 5

WS_SIMPLE = 1
WS_DEDICATE = 4
WS_GROUPCHAT = 5

WS_EVT_INIT = "init"
WS_EVT_OPEN = "open"
WS_EVT_CLOSE = "close"
WS_EVT_NONE = None

WS_MSG_JSON = "json"
WS_MSG_XMLRPC = "xmlrpc"
WS_MSG_GRPC = "grpc"
WS_MSG_DEFAULT = None

WS_OPCODE_TEXT = 0x1
WS_OPCODE_BINARY = 0x2
WS_OPCODE_CLOSE = 0x8
WS_OPCODE_PING = 0x9
WS_OPCODE_PONG = 0xa

from aquests.dbapi import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB
PROTO_HTTP = "http"
PROTO_HTTPS = "https"
PROTO_WS = "ws"
PROTO_WSS = "wss"

class _WASPool:
	def __init__ (self):
		self.__wasc = None
		self.__p = {}
		
	def __get_id (self):
		return id (threading.currentThread ())
	
	def __repr__ (self):
		return "<class skitai.WASPool at %x>" % id (self)
			
	def __getattr__ (self, attr):
		_was = self._get ()
		if not _was.in__dict__ ("app") and hasattr (_was, 'request'):
			# it will be called WSGI middlewares except Saddle,
			# So request object not need
			del _was.request			
		return  getattr (_was, attr)
			
	def __setattr__ (self, attr, value):
		if attr.startswith ("_WASPool__"):
			self.__dict__[attr] = value
		else:	
			setattr (self.__wasc, attr, value)
			for _id in self.__p:
				setattr (self.__p [_id], attr, value)
	
	def __delattr__ (self, attr):
		delattr (self.__wasc, attr)
		for _id in self.__p:
			delattr (self.__p [_id], attr, value)
	
	def _start (self, wasc):
		self.__wasc = wasc
	
	def _del (self):
		_id = self.__get_id ()
		try:
			del self.__p [_id]
		except KeyError:
			pass

	def _get (self):
		_id = self.__get_id ()
		try:
			return self.__p [_id]
		except KeyError:
			_was = self.__wasc ()
			self.__p [_id] = _was
			return _was


was = _WASPool ()
def start_was (wasc):
	global was
	was._start (wasc)


#------------------------------------------------
# Configure
#------------------------------------------------
dconf = {'mount': {"default": []}, 'clusters': {}, 'cron': [], 'max_ages': {}}

def pref ():
	from .saddle.Saddle import Config
	
	d = AttrDict ()
	d.config = Config ()
	return d
	
def getswd ():
	return os.path.dirname (os.path.join (os.getcwd (), sys.argv [0]))

def is_devel ():
	return not os.environ.get ('SKITAI_PRODUCTION')
	
def joinpath (*pathes):
	return os.path.normpath (os.path.join (getswd (), *pathes))
abspath = joinpath
	
def set_max_age (path, max_age):
	global dconf
	dconf ["max_ages"][path] = max_age	

def set_max_rcache (objmax):
	global dconf
	dconf ["rcache_objmax"] = objmax

def set_keep_alive (timeout):	
	dconf ["keep_alive"] = timeout

def set_network_timeout (timeout):
	dconf ["network_timeout"] = timeout
	
def mount (point, target, appname = "app", pref = None, host = "default"):
	global dconf
	
	def init_app (modpath, pref):
		modinit = os.path.join (os.path.dirname (modpath), "__init__.py")
		if os.path.isfile (modinit):
			loader = machinery.SourceFileLoader('temp', modinit)
			mod = loader.load_module()
			hasattr (mod, "bootstrap") and mod.bootstrap (pref)
	
	if type (target) is tuple: 
		module, appfile = target
		target = os.path.join (os.path.dirname (module.__file__), "export", "skitai", appfile)
	if type (target) is not str:
		# app instance
		target = os.path.join (os.getcwd (), sys.argv [0])
	else:
		appname = ""
		if target [0] != "@":		
			target = os.path.join (getswd (), target)
	
	if host not in dconf ['mount']:
		dconf ['mount'][host] = []
	if os.path.isdir (target):
		dconf ['mount'][host].append ((point, target, None))
	else:	
		init_app (target, pref)
		if appname:
			app = (target, appname)
		else:
			app = target
		dconf ['mount'][host].append ((point, app, pref))
	
def cron (sched, cmd):
	global dconf
	dconf ["cron"].append ('%s %s' % (sched, cmd))

def alias (name, ctype, members, role = "", source = "", ssl = False):
	from .server.rpc.cluster_manager import AccessPolicy
	global dconf	
	if name [0] == "@":
		name = name [1:]	
	policy = AccessPolicy (role, source)
	args = (ctype, members, policy, ssl)
	dconf ["clusters"][name] = args	

def enable_forward (forward_to = 443, port = 80, ip = ""):
	global dconf
	dconf ['fws_address'] = ip
	dconf ['fws_port'] = forward_to
	dconf ['fws_to'] = port
		
def enable_gateway (enable_auth = False, secure_key = None, realm = "Skitai API Gateway"):
	global dconf
	dconf ["enable_gw"] = True
	dconf ["gw_auth"] = enable_auth,
	dconf ["gw_realm"] = realm,
	dconf ["gw_secret_key"] = secure_key

def enable_cachefs (memmax = 0, diskmax = 0, path = None):
	global dconf	
	dconf ["cachefs_memmax"] = memmax
	dconf ["cachefs_dir"] = path
	dconf ["cachefs_diskmax"] = diskmax	
				
def enable_proxy (unsecure_https = False):
	global dconf
	dconf ["proxy"] = True
	dconf ["proxy_unsecure_https"] = unsecure_https

def enable_blacklist (path):
	global dconf
	dconf ["blacklist_dir"] = path

def enable_ssl (certfile, keyfile, passphrase):
	global dconf			
	dconf ["certfile"] = certfile
	dconf ["keyfile"] = keyfile
	dconf ["passphrase"] = passphrase
	
def enable_smtpda (server = None, user = None, password = None, ssl = None, max_retry = None, keep_days = None):
	global dconf
	smtpda = {}
	if server: smtpda ["user"] = user
	if password: smtpda ["password"] = password
	if ssl: smtpda ["ssl"] = ssl
	if max_retry: smtpda ["max-retry"] = max_retry
	if keep_days: smtpda ["keep-days"] = keep_days
	dconf ["smtpda"] = smtpda

def run (**conf):
	import os, sys, time
	from . import lifetime
	from .server import Skitai	
	from .server.wastuff import process, daemon	
	from aquests.lib import flock
	import getopt
		
	class SkitaiServer (Skitai.Loader):
		NAME = 'instance'
		
		def __init__ (self, conf):
			self.conf = conf
			self.children = []
			self.flock = None
			Skitai.Loader.__init__ (self, 'config', conf.get ('logpath'), conf.get ('varpath'))
			
		def close (self):
			if self.wasc.httpserver.worker_ident == "master":
				if self.children:
					for child in self.children:
						self.wasc.logger ("server", "[info] try to kill %s..." % child.name)
						child.kill ()				
					
					for i in range (30):
						time.sleep (1)
						veto = False
						for child in self.children:
							veto = (child.poll () is None)
							if veto:
								self.wasc.logger ("server", "[info] %s is still alive" % child.name)
								break														
						if not veto:
							break
					
					if veto:
						for child in self.children:
							if child.poll () is None:
								self.wasc.logger ("server", "[info] force to kill %s..." % child.name)
								child.send_signal ('kill')
			
			Skitai.Loader.close (self)
			
		def create_process (self, name, args, karg):
			argsall = []
			if self.conf.get ("varpath"):
				karg ['var-path'] = self.conf.get ("varpath")
			if self.conf.get ("logpath"):
				karg ['log-path'] = self.conf.get ("logpath")
			if self.conf.get ("verbose", "no") in ("yes", 1, "1"):
				karg ['verbose'] = "yes"
		
			if karg:
				for k, v in karg.items ():
					if len (k) == 1:
						h = "-"
					else:
						h = "--"
					if v is None:
						argsall.append ('%s%s' % (h, k))
					else:
						argsall.append ('%s%s "%s"' % (h, k, str (v).replace ('"', '\\"')))
			
			if args:
				for each in args:
					argsall.append ('"%s"' % each.replace ('"', '\\"'))
								
			cmd = "%s %s %s" % (
				sys.executable, 
				os.path.join (os.path.dirname (Skitai.__file__), "bin", name + ".py"), 
				" ".join (argsall)
			)
			
			self.children.append (
				process.Process (
					cmd, 
					name,
					self.get_varpath ()
				)
			)
		
		def get_varpath (self):
			return self.conf.get ('varpath', daemon.get_default_varpath ())
			
		def config_logger (self, path):
			media = []
			if path is not None:
				media.append ("file")
			if self.conf.get ('verbose', "no") in ("yes", "1", 1):				
				media.append ("screen")
				self.conf ['verbose'] = "yes"
			if not media:
				media.append ("screen")
				self.conf ['verbose'] = "yes"
			Skitai.Loader.config_logger (self, path, media)					
		
		def maintern_shutdown_request (self, now):
			req = self.flock.lockread ("signal")
			if not req: return
			self.wasc.logger ("server", "[info] got signal - %s" % req)
			if req == "terminate":			
				lifetime.shutdown (0, 30.0)
			elif req == "restart":			
				lifetime.shutdown (3, 30.0)
			elif req == "kill":
				lifetime.shutdown (0, 1.0)
			elif req == "rotate":
				self.wasc.logger.rotate ()
			else:
				self.wasc.logger ("server", "[error] unknown signal - %s" % req)
			self.flock.unlock ("signal")
			
		def configure (self):
			conf = self.conf
			smtpda = conf.get ('smtpda')
			if smtpda is not None:
				self.create_process ('smtpda', [], smtpda)			
			cron = conf.get ('cron')
			if cron:
				self.create_process ('cron', cron, {})
			
			self.set_num_worker (conf.get ('workers', 1))
			if conf.get ("certfile"):
				self.config_certification (conf.get ("certfile"), conf.get ("keyfile"), conf.get ("passphrase"))
			
			if conf.get ("cachefs_diskmax", 0) and not conf.get ("cachefs_dir"):
				conf ["cachefs_dir"] = os.path.join (self.get_varpath (), "cachefs")

			self.config_cachefs (
				conf.get ("cachefs_dir", None), 
				conf.get ("cachefs_memmax", 0),
				conf.get ("cachefs_diskmax", 0)				
			)
			self.config_rcache (conf.get ("rcache_objmax", 100))
			if conf.get ('fws_to'):
				self.config_forward_server (
					conf.get ('fws_address', '0.0.0.0'), conf.get ('fws_port', 80), conf.get ('fws_to', 443)
				)
			self.config_webserver (
				conf.get ('port', 5000), conf.get ('address', '0.0.0.0'),
				NAME, conf.get ("certfile") is not None,
				conf.get ('keep_alive', 30), 
				conf.get ('network_timeout', 30), 
			)
			
			if os.name == "posix" and self.wasc.httpserver.worker_ident == "master":
				# master does not serve
				return
			
			self.config_threads (conf.get ('threads', 4))						
			for name, args in conf.get ("clusters", {}).items ():				
				ctype, members, policy, ssl = args
				self.add_cluster (ctype, name, members, ssl, policy)
			
			self.install_handler (
				conf.get ("mount"), 
				conf.get ("proxy", False),
				conf.get ("max_ages", {}),
				conf.get ("blacklist_dir"), # blacklist_dir
				conf.get ("proxy_unsecure_https", False), # disable unsecure https
				conf.get ("enable_gw", False), # API gateway
				conf.get ("gw_auth", False),
				conf.get ("gw_realm", "API Gateway"),
				conf.get ("gw_secret_key", None)
			)
			
			lifetime.init ()
			if os.name == "nt":				
				lifetime.maintern.sched (10.0, self.maintern_shutdown_request)
				self.flock = flock.Lock (os.path.join (self.get_varpath (), ".%s" % self.NAME))
	
	#----------------------------------------------------------------------------
	def start (working_dir):
		if os.name == "nt":
			raise SystemError ('Daemonizing not supported')		
		from .daemonize import Daemonizer
		Daemonizer (working_dir).runAsDaemon ()
			
	def stop (working_dir):
		import signal
		pidfile = os.path.join (working_dir, '.pid')
		if not os.path.isfile (pidfile):
			raise SystemError ('Cannot find process')
		with open (pidfile, "r") as f:
			pid = int (f.read ())
		os.kill (pid, signal.SIGTERM)
		os.remove (pidfile)
		return
	
	#----------------------------------------------------------------------------
	
	global dconf
	
	for k, v in dconf.items ():
		if k not in conf:
			conf [k] = v
				
	if not conf.get ('mount'):
		raise systemError ('No mount point')
	
	argopt = getopt.getopt(sys.argv[1:], "vfdsr", [])
	working_dir = getswd ()
	try: cmd = argopt [1][0]
	except: cmd = None
	karg = {}
	for k, v in argopt [0]:
		if k == "-d": cmd = "start"
		elif k == "-r": cmd = "retart"
		elif k == "-s": cmd = "stop"
		else: karg [k] = v
			
	if cmd in ("start", "restart") and '-v' in karg:
		raise SystemError ('Daemonizer cannot be run with -v, It is meaningless')
				
	if cmd == "stop":
		return stop (working_dir)
	elif cmd == "start":
		start (working_dir)
	elif cmd == "restart":
		stop (working_dir)
		start (working_dir)	
		
	verbose = 0
	if '-v' in karg or conf.get ('logpath') is None:
		verbose = 1
	
	if "-f" in karg:
		# failsafe run
		from . import failsafer
		failsafer.Service (
			"%s %s %s" % (sys.executable, os.path.join (os.getcwd (), sys.argv [0]), verbose and '-v' or ''),
			conf.get ('logpath'),
			conf.get ('varpath'),
			'-v' in karg
		).run ()
	
	else:
		os.chdir (working_dir)
		if verbose:
			conf ['verbose'] = 'yes'
		server = SkitaiServer (conf)
		# timeout for fast keyboard interrupt on win32	
		try:
			try:
				server.run (conf.get ('verbose') and 2.0 or 30.0)
			except KeyboardInterrupt:
				pass	
		
		finally:	
			_exit_code = server.get_exit_code ()
			if _exit_code is not None: # master process				
				sys.exit (_exit_code)
			else: # worker process				
				sys.exit (lifetime._exit_code)
			