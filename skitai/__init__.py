# 2014. 12. 9 by Hans Roh hansroh@gmail.com

__version__ = "0.25.7"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  __version__.split (".")))
NAME = "SWAE/%s.%s" % version_info [:2]

import threading
import sys
import h2

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
			if self.conf.get ("verbose"):
				karg ['verbose'] = self.conf.get ("verbose")
		
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
			print (cmd)
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
			if self.conf.get ('verbose', 1):
				media.append ("screen")			
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
			if cron is not None:
				self.create_process ('cron', cron, {})
			
			self.set_num_worker (conf.get ('workers', 1))
			if conf.get ("certfile"):
				self.config_certification (conf.get ("certfile"), conf.get ("keyfile"), conf.get ("passphrase"))
			self.config_cachefs ()
			self.config_rcache (100)
			self.config_webserver (
				conf.get ('port', 5000), conf.get ('address', '0.0.0.0'),
				"Skitai Server", conf.get ("certfile") is not None,
				5, 10
			)
			self.config_threads (conf.get ('threads', 4))						
			for name, args in conf.get ("clusters", {}).items ():
				if name [0] == "@":
					name = name [1:]
				if len (args) == 3:
					ctype, members, ssl = args
				else:
					ctype, members = args	
					ssl = 0
				self.add_cluster (ctype, name, members, ssl)
			
			self.install_handler (
				conf.get ("mount"), 
				conf.get ("proxy", False),
				conf.get ("static_max_age", 300),
				None, # blacklistdir
				False, # disable unsecure https
				conf.get ("enable_gw", False), # API gateway
				conf.get ("gw_auth", False),
				conf.get ("gw_realm", "API Gateway"),
				conf.get ("gw_secret_key", None)
			)
			
			lifetime.init ()
			if os.name == "nt":				
				lifetime.maintern.sched (10.0, self.maintern_shutdown_request)
				self.flock = flock.Lock (os.path.join (self.get_varpath (), "lock.%s" % self.NAME))
				
	if not conf.get ('mount'):
		raise ValueError ('Dictionary mount {mount point: path or app} required')
	
	argopt = getopt.getopt(sys.argv[1:], "vs", [])
	karg = {}
	for k, v in argopt [0]:
		karg [k] = v
			
	if "-s" in karg:
		from skitai import skitaid
		skitaid.Service (
			"%s %s %s" % (sys.executable, os.path.join (os.getcwd (), sys.argv [0]), '-v' in karg and '-v' or ''),
			conf.get ('logpath'),
			conf.get ('varpath'),
			'-v' in karg
		).run ()
	
	else:
		os.chdir (os.path.dirname (os.path.join (os.getcwd (), sys.argv [0])))
		if '-v' in karg:			
			conf ['verbose'] = 1
		server = SkitaiServer (conf)
		# timeout for fast keyboard interrupt on win32	
		try:
			server.run (os.name == "nt"  and conf.get ('verbose') and 2.0 or 30.0)
		
		finally:	
			_exit_code = server.get_exit_code ()
			if _exit_code is not None: # master process
				sys.exit (_exit_code)
			else: # worker process				
				sys.exit (lifetime._exit_code)	
			