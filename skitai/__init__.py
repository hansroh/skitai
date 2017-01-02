# 2014. 12. 9 by Hans Roh hansroh@gmail.com

VERSION = "0.21.15"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  VERSION.split (".")))
NAME = "SWAE/%s.%s" % version_info [:2]

import threading
import sys
HTTP2 = True
try: import h2
except ImportError: HTTP2 = False

WEBSOCKET_REQDATA = 1
WEBSOCKET_DEDICATE = 2
WEBSOCKET_MULTICAST = 3
WEBSOCKET_DEDICATE_THREADSAFE = 4

DB_PGSQL = "*postgresql"
DB_SQLITE3 = "*sqlite3"
DB_REDIS = "*redis"
DB_MONGODB = "*mongodb"

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
		if not _was.in__dict__ ("app"):
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
	from . import lifetime
	from .server import Skitai
	
	class TestServer (Skitai.Loader):
		def __init__ (self, conf):
			self.conf = conf
			Skitai.Loader.__init__ (self, 'test.conf')
			
		def configure (self):
			conf = self.conf
			
			self.set_num_worker (1)
			if conf.get ("certfile"):		
				self.config_certification (conf.get ("certfile"), conf.get ("keyfile"), conf.get ("passphrase"))
			self.config_rcache (100)
			self.config_webserver (
				conf.get ('port', 5000), conf.get ('address', '127.0.0.1'), 
				"Skitai Test Server", conf.get ("certfile") is not None, 
				5, 10
			)
			self.config_threads (conf.get ('threads', 4))
			
			for name, (ctype, members, ssl) in conf.get ("clusters", {}):
				self.add_cluster (ctype, name, members, ssl)
			
			self.install_handler (
				conf.get ("mount"), 
				conf.get ("proxy", False),
				conf.get ("static_max_age", 300)
			)
			lifetime.init ()
	
	if not conf.get ('mount'):
		raise ValueError ('Dictionary mount {mount point: path or app} required')
	
	server = TestServer (conf)
	# timeout for fast keyboard interrupt on win32	
	server.run (2.0)
	
	