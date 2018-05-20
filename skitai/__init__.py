# 2014. 12. 9 by Hans Roh hansroh@gmail.com

__version__ = "0.27"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  __version__.split (".")))
NAME = "Skitai/%s.%s" % version_info [:2]

import threading
import sys, os
import h2
from aquests.lib import versioning
from aquests.lib.attrdict import AttrDict
from aquests.protocols.dns import asyndns
from importlib import machinery
from .server.wastuff import process, daemon	as wasdaemon
from aquests.dbapi import DB_PGSQL, DB_POSTGRESQL, DB_SQLITE3, DB_REDIS, DB_MONGODB
from .launcher import launch
from aquests.protocols.smtp import composer

PROTO_HTTP = "http"
PROTO_HTTPS = "https"
PROTO_WS = "ws"
PROTO_WSS = "wss"
DJANGO = "django"

WEBSOCKET_SIMPLE = 1
WEBSOCKET_GROUPCHAT = 5

WS_SIMPLE = 1
WS_THREADSAFE = 6
WS_GROUPCHAT = 5

WS_EVT_INIT = "init"
WS_EVT_OPEN = "open"
WS_EVT_CLOSE = "close"
WS_EVT_NONE = None

WS_MSG_JSON = "json"
WS_MSG_XMLRPC = "xmlrpc"
WS_MSG_GRPC = "grpc"
WS_MSG_TEXT = "text"
WS_MSG_DEFAULT = "text"

WS_OPCODE_TEXT = 0x1
WS_OPCODE_BINARY = 0x2
WS_OPCODE_CLOSE = 0x8
WS_OPCODE_PING = 0x9
WS_OPCODE_PONG = 0xa


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
dconf = {'mount': {"default": []}, 'clusters': {}, 'cron': [], 'max_ages': {}, 'log_off': [], 'dns_protocol': 'tcp'}

def pref (preset = False):
	from .saddle.Saddle import Config
	
	d = AttrDict ()
	d.config = Config (preset)
	return d

def get_proc_title ():
	a, b = os.path.split (os.path.join (os.getcwd (), sys.argv [0]))
	return "skitai(%s/%s)" % (
		os.path.basename (a),
		b.split(".")[0]
	)
	
def getswd ():
	return os.path.dirname (os.path.join (os.getcwd (), sys.argv [0]))

def is_devel ():
	return os.environ.get ('SKITAI_ENV') != "PRODUCTION"

def joinpath (*pathes):
	return os.path.normpath (os.path.join (getswd (), *pathes))
abspath = joinpath

Win32Service = None
def set_service (service_class):
	global Win32Service	
	Win32Service = service_class

def set_worker_critical_point (cpu_percent = 90.0, continuous = 3, interval = 20):
	from .server.http_server import http_server
	from .server.https_server import https_server	
	
	http_server.critical_point_cpu_overload = https_server.critical_point_cpu_overload = cpu_percent
	http_server.critical_point_continuous = https_server.critical_point_continuous = continuous
	http_server.maintern_interval = https_server.maintern_interval = interval

def log_off (*path):		
	global dconf
	for each in path:
		dconf ['log_off'].append (each)	

def set_dns_protocol (protocol = 'tcp'):		
	global dconf
	dconf ['dns_protocol'] = protocol
	
def set_max_age (path, max_age):
	global dconf
	dconf ["max_ages"][path] = max_age

def set_max_rcache (objmax):
	global dconf
	dconf ["rcache_objmax"] = objmax

def set_keep_alive (timeout):	
	global dconf
	dconf ["keep_alive"] = timeout

def set_backend_keep_alive (timeout):	
	global dconf
	dconf ["backend_keep_alive"] = timeout

def set_proxy_keep_alive (channel = 60, tunnel = 600):	
	from .server.handlers import proxy

	proxy.PROXY_KEEP_ALIVE = channel
	proxy.PROXY_TUNNEL_KEEP_ALIVE = tunnel
		
def set_request_timeout (timeout):
	global dconf	
	dconf ["network_timeout"] = timeout
set_network_timeout = set_request_timeout

def deflu (*key):
	if "models-keys" not in dconf:
		dconf ["models-keys"] = []
	if isinstance (key [0], (list, tuple)):
		key = list (key [0])
	dconf ["models-keys"].extend (key)
addlu = trackers = lukeys = deflu

def __is_django (wsgi_path, appname):
	if not isinstance (wsgi_path, str):
		return
	if appname != "application":
		return
	settings = os.path.join (os.path.dirname (wsgi_path), 'settings.py')
	if os.path.exists (settings):
		root = os.path.dirname (os.path.dirname (wsgi_path))
		sys.path.insert (0, root)
		alias_django ("@" + os.path.basename (root), settings)
		return root
	
def mount (point, target, appname = "app", pref = pref (True), host = "default", path = None):
	global dconf
	
	def init_app (modpath, pref):
		modinit = os.path.join (os.path.dirname (modpath), "__init__.py")
		if os.path.isfile (modinit):
			loader = machinery.SourceFileLoader('temp', modinit)
			mod = loader.load_module()
			hasattr (mod, "bootstrap") and mod.bootstrap (pref)

	maybe_django = __is_django (target, appname)		
	if path:
		if isinstance (path, str):
			path = [path]
		path.reverse ()	
		for each in path:			
			sys.path.insert (0, abspath (each))
			
	if hasattr (target, "__file__"):
		target = (target, '__export__.py')
	
	if type (target) is tuple:
		module, appfile = target
		target = os.path.join (os.path.dirname (module.__file__), "export", "skitai", appfile)
			
	if type (target) is not str:
		# app instance, find app location
		target = os.path.normpath (os.path.join (os.getcwd (), sys.argv [0]))		
	else:
		if target [0] == "@":
			appname = None
		else:
			target = joinpath (target)
			
	if host not in dconf ['mount']:
		dconf ['mount'][host] = []

	if os.path.isdir (target) or not appname:
		dconf ['mount'][host].append ((point, target, None))
	else:		
		init_app (target, pref)
		dconf ['mount'][host].append ((point,  (target, appname), pref))
		
mount_django = mount
	
def cron (sched, cmd):
	global dconf
	dconf ["cron"].append ('%s %s' % (sched, cmd))

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

def _get_django_settings (settings_path):
	import importlib
	import django
	
	ap = abspath (settings_path)
	django_main, settings_file = os.path.split (ap)
	django_root, django_main_dir = os.path.split (django_main)
	settings_mod = "{}.{}".format (django_main_dir, settings_file.split (".")[0])
	
	if not os.environ.get ("DJANGO_SETTINGS_MODULE"):		
		sys.path.insert (0, django_root)		
		os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_mod)
		django.setup()
	
	return importlib.import_module(settings_mod).DATABASES

def alias_django (name, settings_path):
	dbsettings = _get_django_settings (settings_path)
	default = dbsettings ['default']
	if default ['ENGINE'].endswith ('sqlite3'):			
		return alias (name, DB_SQLITE3, default ['NAME'])
	
	if default ['ENGINE'].find ("postgresql") != -1:	
		if not default.get ("PORT"):
			default ["PORT"] = 5432
		if not default.get ("HOST"):
			default ["HOST"] = "127.0.0.1"
		if not default.get ("USER"):
			default ["USER"] = ""
		if not default.get ("PASSWORD"):
			default ["PASSWORD"] = ""
		return alias (name, DB_PGSQL, "%(HOST)s:%(PORT)s/%(NAME)s/%(USER)s/%(PASSWORD)s" % default)

@versioning.deprecated
def use_django_models (settings_path, name = None):
	if name:
		alias = alias_django (name, settings_path)		
	return _get_django_settings (settings_path)	

def alias (name, ctype, members, role = "", source = "", ssl = False, django = None):
	from .server.rpc.cluster_manager import AccessPolicy
	global dconf
	
	if name [0] == "@":
		name = name [1:]
	if dconf ["clusters"].get (name):
		return
	
	if ctype == DJANGO:
		alias = alias_django (name, members)
		if alias is None:
			raise SystemError ("Database engine is not compatible")
		return alias
	
	policy = AccessPolicy (role, source)
	args = (ctype, members, policy, ssl)
	dconf ["clusters"][name] = args
	return name, args

def enable_cachefs (memmax = 0, diskmax = 0, path = None):
	global dconf	
	dconf ["cachefs_memmax"] = memmax
	dconf ["cachefs_dir"] = path
	dconf ["cachefs_diskmax"] = diskmax	
				
def enable_proxy (unsecure_https = False):
	global dconf
	dconf ["proxy"] = True
	dconf ["proxy_unsecure_https"] = unsecure_https
	if os.name == "posix": 
		dconf ['dns_protocol'] = 'udp'

def enable_file_logging (path = None):
	global dconf
	if not path:
		dconf ['logpath'] = wasdaemon.get_default_logpath ()
	
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
	if server: smtpda ["server"] = server
	if user: smtpda ["user"] = user
	if password: smtpda ["password"] = password
	if ssl: smtpda ["ssl"] = ssl
	if max_retry: smtpda ["max-retry"] = max_retry
	if keep_days: smtpda ["keep-days"] = keep_days
	dconf ["smtpda"] = smtpda
	
def run (**conf):
	import os, sys, time
	from . import lifetime
	from .server import Skitai
	from aquests.lib.pmaster import flock
	from aquests.lib import pathtool
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
						self.wasc.logger ("server", "[info] killing %s..." % child.name)						
						child.kill (0)
					
					for i in range (10):
						time.sleep (1)
						veto = False
						for child in self.children:
							veto = (child.poll () is None)
							if veto:
								if i % 3 == 0:
									self.wasc.logger ("server", "[info] %s is still alive" % child.name)
								break
						if not veto:
							break
					
					if veto:
						for child in self.children:
							if child.poll () is None:
								self.wasc.logger ("server", "[info] force to kill %s..." % child.name)
								child.kill (1)
			
			Skitai.Loader.close (self)
			
		def create_process (self, name, args, karg):
			argsall = []
			karg ['pname'] = get_proc_title ()
			karg ['var-path'] = self.varpath
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
				"{}skitai-{}".format (os.name == "posix" and "/usr/local/bin/" or "", name), 
				" ".join (argsall)
			)
			
			self.children.append (
				process.Process (
					cmd, 
					name,
					self.varpath
				)
			)
			
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
			Skitai.Loader.config_logger (self, path, media, self.conf ["log_off"])
		
		def master_jobs (self):
			smtpda = self.conf.get ('smtpda')
			if smtpda is not None:
				self.create_process ('smtpda', [], smtpda)				
				composer.Composer.SAVE_PATH = os.path.join (self.varpath, "smtpda", "mail", "spool")
				
			cron = self.conf.get ('cron')
			if cron:
				self.create_process ('cron', cron, {})
			
			self.wasc.logger ("server", "[info] engine tmp path: %s" % self.varpath)
			if self.logpath:
				self.wasc.logger ("server", "[info] engine log path: %s" % self.logpath)
			
			self.conf.get ("models-keys") and self.set_model_keys (self.conf ["models-keys"])
						
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
			self.set_num_worker (conf.get ('workers', 1))
			if conf.get ("certfile"):
				self.config_certification (conf.get ("certfile"), conf.get ("keyfile"), conf.get ("passphrase"))
			
			self.config_dns (dconf ['dns_protocol'])
			if conf.get ("cachefs_diskmax", 0) and not conf.get ("cachefs_dir"):
				conf ["cachefs_dir"] = os.path.join (self.varpath, "cachefs")

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
				thunks = [self.master_jobs]
			)
			
			if os.name == "posix" and self.wasc.httpserver.worker_ident == "master":
				# master does not serve
				return			
			
			self.config_threads (conf.get ('threads', 4))			
			self.config_backends (conf.get ('backend_keep_alive', 1200))
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
			
			lifetime.init (logger = self.wasc.logger.get ("server"))
			lifetime.maintern.sched (3.0, asyndns.pool.maintern)
			if os.name == "nt":
				lifetime.maintern.sched (11.0, self.maintern_shutdown_request)								
				self.flock = flock.Lock (os.path.join (self.varpath, ".%s" % self.NAME))
			
	#----------------------------------------------------------------------------
	if os.name == "nt":
		import win32serviceutil
		
		def set_service_config (argv = []):
			global Win32Service			
			#sys.stdout = sys.stderr = open (r"D:\apps\skitai\examples\err.log", "a")
			argv.insert (0, "")			
			script = os.path.join (os.getcwd (), sys.argv [0])
			win32serviceutil.HandleCommandLine(Win32Service, "%s.%s" % (script [:-3], Win32Service.__name__), argv)
				
		def install (working_dir):
			set_service_config (['--startup', 'auto', 'install'])
	
		def remove (working_dir):
			set_service_config (['remove'])
		
		def update (working_dir):
			set_service_config (['update'])
				
	def start (working_dir, lockpath):
		if os.name == "nt":
			set_service_config (['start'])
		else:	
			from aquests.lib.pmaster import Daemonizer
			if not Daemonizer (working_dir, 'skitai', lockpath = lockpath).runAsDaemon ():
				print ("already running")
				sys.exit ()
			
	def stop (lockpath):
		if os.name == "nt":			
			set_service_config (['stop'])
		else:	
			from aquests.lib.pmaster import daemon
			daemon.kill (lockpath, 'skitai', True)
	
	def status (lockpath, verbose = True):
		from aquests.lib.pmaster import daemon
		pid = daemon.status (lockpath, 'skitai')
		if verbose:
			if pid:
				print ("running [%d]" % pid)
			else:
				print ("stopped")
		return pid	
	
	#----------------------------------------------------------------------------
	
	global dconf
	
	for k, v in dconf.items ():
		if k not in conf:
			conf [k] = v
				
	if not conf.get ('mount'):
		raise systemError ('No mount point')
	
	argopt = getopt.getopt(sys.argv[1:], "vfdsr", [])	
	conf ["varpath"] = wasdaemon.get_default_varpath ()
	pathtool.mkdir (conf ["varpath"])
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
	
	lockpath = conf ["varpath"] 		
	if cmd == "stop":
		return stop (lockpath)
	elif cmd == "status":
		return status (lockpath)
	elif cmd == "start":
		start (working_dir, lockpath)		
	elif cmd == "install":	
		install (working_dir)
	elif cmd == "update":	
		update ()
	elif cmd == "remove":	
		remove (working_dir)	
	elif cmd == "restart":
		stop (lockpath)		
		time.sleep (2)
		start (working_dir, lockpath)
	elif cmd:
		print ('unknown command: %s' % cmd)
		return
	
	if cmd and os.name == "nt":
		return
				
	verbose = 0
	if '-v' in karg:
		verbose = 1
	
	if "-f" in karg:
		if os.name != "nt":
			 raise SystemError ('-v option is needed only on win32')
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
		else:
			sys.stderr = open (os.path.join (conf.get ('varpath'), "stderr.engine"), "a")	
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
			else: 
				# worker process				
				# for avoiding multiprocessing.manager process's join error
				os._exit (lifetime._exit_code)
			
