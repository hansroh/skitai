import os, sys, re, types, time
from rs4  import pathtool, importer, evbus
import threading
from types import FunctionType as function
import copy
from skitai import lifetime
import inspect
from rs4 import attrdict
from importlib import reload

def set_default (cf):
	cf.max_post_body_size = 1 * 1024 * 1024
	cf.max_cache_size = 1 * 1024 * 1024
	cf.max_multipart_body_size = 20 * 1024 * 1024
	cf.max_upload_file_size = 20 * 1024 * 1024
	
def Config (preset = False):
	cf = attrdict.AttrDict ()
	if preset:
		set_default (cf)		
	return cf


class Module:
	def __init__ (self, wasc, handler, bus, route, directory, libpath, pref = None):
		self.wasc = wasc
		self.bus = bus
		self.handler = handler
		self.pref = pref
		self.last_reloaded = time.time ()
		self.app = None
		self.django = False
		self.set_route (route)
		self.directory = directory
		self.has_life_cycle = False
				
		if type (libpath) is str:
			try:
				libpath, self.appname = libpath.split (":", 1)		
			except ValueError:
				libpath, self.appname = libpath, "app"
			self.libpath = libpath
			self.script_name = "%s.py" % libpath
			self.module, self.abspath = importer.importer (directory, libpath)
			self.start_app ()
			
		else:
			# libpath is app object, might be added by unittest
			self.appname, self.module, self.abspath = "app", None, os.path.join (directory, 'dummy')
			self.app = libpath
			self.app.use_reloader = False
			self.start_app ()
		
		app = self.app or getattr (self.module, self.appname)
		self.has_life_cycle and app.life_cycle ("before_mount", self.wasc)
		
	def __repr__ (self):
		return "<Module routing to %s at %x>" % (self.route, id(self))
				
	def get_callable (self):
		return self.app or getattr (self.module, self.appname)
		
	def start_app (self, reloded = False):
		func = None
		app = self.app or getattr (self.module, self.appname)
		if hasattr (app, "set_logger"):
			app.set_logger (self.wasc.logger.get ("app"))		
		self.django = str (app.__class__).find ("django.") != -1
		self.has_life_cycle = hasattr (app, "life_cycle")
		
		if self.pref:
			for k, v in copy.copy (self.pref).items ():
				if k == "config":
					if not hasattr (app, 'config'):
						app.config = v
					else:	
						for k, v in copy.copy (self.pref.config).items ():
							app.config [k] = v
				else:
					setattr (app, k, v)					
		
		if hasattr (app, "_aliases"):
			while app._aliases:
				self.wasc.add_cluster (*app._aliases.pop (0))			

		if not hasattr (app, "config"):
			app.config = Config (True)
								
		elif not hasattr (app.config, "max_post_body_size"):
			set_default (app.config)
		
		if hasattr (app, "mountables"):
			for _args, _karg in app.mountables:
				app.mount (*_args, **_karg)			
		
		if hasattr (app, "max_client_body_size"):
			val = app.max_client_body_size
			app.config.max_post_body_size = val
			app.config.max_multipart_body_size = val
			app.config.max_upload_file_size = val

		if hasattr (app, "set_home"):
			app.set_home (os.path.dirname (self.abspath), self.module)

		if hasattr (app, "commit_events_to"):
			app.commit_events_to (self.bus)

		self.set_devel_env ()
		self.update_file_info ()
			
		try:			
			if not reloded:
				func = app.start 
			else:
				func = app.restart
		except AttributeError:			
			pass
			
		if func:
			# temporary current handler
			self.wasc.handler = self.handler
			func (self.wasc, self.route)
			self.wasc.handler = None
	
	def mounted (self):
		app = self.app or getattr (self.module, self.appname)
		self.has_life_cycle and app.life_cycle ("mounted", self.wasc ())
		self.has_life_cycle and app.life_cycle ("mounted_or_reloaded", self.wasc ())
		
	def umounted (self):
		app = self.app or getattr (self.module, self.appname)
		self.has_life_cycle and app.life_cycle ("umounted", self.wasc)
			
	def cleanup (self):
		app = self.app or getattr (self.module, self.appname)
		self.has_life_cycle and app.life_cycle ("before_umount", self.wasc ())
		try: app.cleanup ()
		except AttributeError: pass		
	
	def check_django_reloader (self, now):
		from django.utils import autoreload
		
		changed = autoreload.code_changed ()		
		if changed:
			self.wasc.logger ("app", "reloading app, %s" % self.abspath, "debug")
			self.last_reloaded = time.time ()			
			lifetime.shutdown (3, 0)	
			
	def set_devel_env (self):
		self.debug = False
		self.use_reloader = False
		app = self.app or getattr (self.module, self.appname)
		
		if os.environ.get ("SKITAI_ENV") == "PRODUCTION":
			app.debug = False
			app.use_reloader = False
			return
		
		try: self.debug = app.debug
		except AttributeError: pass
		try: self.use_reloader = app.use_reloader
		except AttributeError: pass
		else:
			if self.use_reloader and self.django:
				lifetime.maintern.sched (1.0, self.check_django_reloader)				
				
	def update_file_info (self):
		if self.module is None:
			# app directly mounted
			return
		stat = os.stat (self.abspath)
		self.file_info = (stat.st_mtime, stat.st_size)	
	
	def maybe_reload (self):
		if not self.use_reloader:
			return
				
		if self.django:
			# see check_django_reloader
			return
			
		if time.time () - self.last_reloaded < 1.0:
			return
			
		stat = os.stat (self.abspath)
		if self.file_info != (stat.st_mtime, stat.st_size):
			oldapp = getattr (self.module, self.appname)
			self.has_life_cycle and oldapp.life_cycle ("before_reload", self.wasc ())
			
			try:
				reloaded = importer.reimporter (self.module, self.directory, self.libpath)			
			except:
				self.module.app = oldapp
				raise
			else:
				if not reloaded:				
					return
				self.module, self.abspath = reloaded
				if hasattr (oldapp, "remove_events"):
					oldapp.remove_events (self.bus)
				PRESERVED = []
				if hasattr (oldapp, "PRESERVE_ON_RELOAD"):
					PRESERVED = [(attr, getattr (oldapp, attr)) for attr in oldapp.PRESERVES_ON_RELOAD]
				
				self.start_app (reloded = True)
				newapp = getattr (self.module, self.appname)
				for attr, value in PRESERVED:
					setattr (newapp, attr, value)
				# reloaded
				self.has_life_cycle and newapp.life_cycle ("reloaded", self.wasc ())
				self.has_life_cycle and newapp.life_cycle ("mounted_or_reloaded", self.wasc ())
				self.last_reloaded = time.time ()
				self.wasc.logger ("app", "reloading app, %s" % self.abspath, "debug")
				
	def set_route (self, route):
		route = route
		while route and route [-1] == "/":
			route = route [:-1]				
		self.route = route + "/"		
		self.route_len = len (self.route) - 1
			
	def get_route (self):
		return self.route
					
	def get_path_info (self, path):
		path_info = ("/" + path) [self.route_len:]
		return path_info	
	
	def __call__ (self, env, start_response):
		self.use_reloader and self.maybe_reload ()
		app = self.app or getattr (self.module, self.appname)
		return app (env, start_response)
		

class ModuleManager:
	modules = {}	
	def __init__(self, wasc, handler):
		self.wasc = wasc
		self.handler = handler
		self.modules = {}
		self.modnames = {}		
		self.bus = evbus.EventBus ()
		self.cc = 0
	
	def __getitem__ (self, name):
		return self.modnames [name].get_callable ()
		
	def build_url (self, thing, *args, **kargs):
		a, b = thing.split (":", 1)
		return self.modnames [a].get_callable ().build_url (b, *args, **kargs)
		
	def add_module (self, route, directory, modname, pref):
		if modname in self.modnames:
			self.wasc.logger ("app", "app file name collision detected '%s'" % modname, "error")			
			return
		
		if not route:
			route = "/"
		elif not route.endswith ("/"):
			route = route + "/"
			
		try: 
			module = Module (self.wasc, self.handler, self.bus, route, directory, modname, pref)			
		except: 
			self.wasc.logger.trace ("app")
			self.wasc.logger ("app", "[error] app load failed: %s" % modname)			
		else: 			
			self.wasc.logger ("app", "[info] app %s mounted" % modname)
			if route in self.modules:
				self.wasc.logger ("app", "[info] app route collision detected: %s at %s <-> %s" % (route, module.abspath, self.modules [route].abspath), "warn")
			self.modules [route] = module
			if type (modname) is str:
				# possibley direct app object
				self.modnames [modname.split (":", 1)[0]] = module
	
	def get_app (self, script_name):		
		route = self.has_route (script_name)		
		if route in (0, 1): # 404, 301
			return None

		try:	
			app = self.modules [route]
		except KeyError:
			return None
		return app	
		
	def has_route (self, script_name):
		# 0: 404
		# 1: 301 => /skitai => /skitai/
		if script_name == "/" and "/" in self.modules:
			return "/"
		
		cands = []
		for route in self.modules:
			if script_name == route:
				cands.append (route)
			elif script_name + "/" == route:
				return 1
			elif script_name.startswith (route [-1] != "/" and route + "/" or route):
				cands.append (route)
				
		if cands:
			if len (cands) == 1:
				return cands [0]
			cands.sort (key = lambda x: len (x))
			return cands [-1]

		elif "/" in self.modules:
			return "/"
						
		return 0
	
	def unload (self, route):
		module = self.modules [route]
		self.wasc.logger ("app", "[info] unloading app: %s" % route)
		try: 
			self.wasc.logger ("app", "[info] ..cleanup app: %s" % route)
			module.cleanup ()
		except AttributeError:
			pass
		except:
			self.wasc.logger.trace ("app")			
		del module
		del self.modules [route]
	
	def cleanup (self):
		self.wasc.logger ("app", "[info] cleanup apps")
		for route, module in list(self.modules.items ()):
			try: 
				self.wasc.logger ("app", "[info] ..cleanup app: %s" % route)					
				module.cleanup ()
			except AttributeError:
				pass
			except:
				self.wasc.logger.trace ("app")			
	
	def status (self):
		d = {}
		for path, module in list(self.modules.items ()):
			d ['<a href="%s">%s</a>' % (path, path)] = module.abspath
		return d


