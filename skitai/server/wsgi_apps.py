import os, sys, re, types
from skitai.lib  import pathtool, importer
import threading
from types import FunctionType as function


class Module:
	def __init__ (self, wasc, route, directory, libpath):
		self.wasc = wasc
		try:
			libpath, self.appname = libpath.split (":", 1)		
		except ValueError:
			libpath, self.appname = libpath, "app"

		self.script_name = "%s.py" % libpath
		self.module, self.abspath = importer.importer (directory, libpath)				
		self.set_route (route)
		self.start_app ()
	
	def get_callable (self):
		return getattr (self.module, self.appname)
		
	def start_app (self, reloded = False):					
		self.set_devel_env ()
		self.update_file_info ()
		try:			
			if not reloded:
				getattr (self.module, self.appname).start (self.wasc, self.route)
			else:
				getattr (self.module, self.appname).restart (self.wasc, self.route)
		except AttributeError:
			pass	
		
	def set_devel_env (self):
		self.debug = False
		self.use_reloader = False
		if type (getattr (self.module, self.appname)) is function:
			try: self.debug = getattr (self.module, "DEBUG")				
			except AttributeError: pass
			try: self.use_reloader = getattr (self.module, "USE_RELOADER")	
			except AttributeError: pass
		else:
			try: self.debug = getattr (self.module, self.appname).debug
			except AttributeError: pass
			try: self.use_reloader = getattr (self.module, self.appname).use_reloader
			except AttributeError: pass

	def update_file_info (self):
		stat = os.stat (self.abspath)
		self.file_info = (stat.st_mtime, stat.st_size)	
	
	def maybe_reload (self):
		stat = os.stat (self.abspath)
		reloadable = self.file_info != (stat.st_mtime, stat.st_size)		
		if reloadable and self.use_reloader:
			importer.reloader (self.module)
			self.start_app (reloded = True)
			return True
		return False
				
	def set_route (self, route):
		route = route
		if not route or route [0] != "/":
			raise TypeError("route url must be abs path")
		while route and route [-1] == "/":
			route = route [:-1]
		if not route:
			route = "/"
		self.route = route
		self.route_len = len (route)
		
	def get_route (self):
		return self.route
					
	def get_path_info (self, path):
		path_info = path [self.route_len:]
		if not path_info: path_info = u"/"
		return path_info	
	
	def cleanup (self):
		try: getattr (self.module, self.appname).cleanup ()
		except AttributeError: pass	
			
	def __call__ (self, env, start_response):
		self.use_reloader and self.maybe_reload ()		
		return getattr (self.module, self.appname) (env, start_response)


class ModuleManager:
	modules = {}	
	def __init__(self, wasc):
		self.wasc = wasc		
		self.modules = {}		
			
	def add_module (self, route, directory, modname):
		if not route:
			route = "/"

		try: 
			module = Module (self.wasc, route, directory, modname)			
			
		except: 
			self.wasc.logger.trace ("app")
			self.wasc.logger ("app", "[error] application load failed: %s" % modname)
			
		else: 
			route = module.get_route ()
			self.wasc.logger ("app", "[info] application %s imported." % route)
			if route in self.modules:
				self.wasc.logger ("app", "[info] application route collision detected: %s at %s <-> %s" % (route, module.abspath, self.modules [route].abspath), "warn")
			self.modules [route] = module
	
	def get_app (self, script_name, rootmatch = False):
		if not rootmatch:
			route = self.has_route (script_name)
			if route in (0, 1): # 404, 301
				return None
		else:
			route = "/"
		
		try:	
			app = self.modules [route]
		except KeyError:
			return None
		
		return app	
		
	def has_route (self, script_name):
		# 0: 404
		# 1: 301
		# route string
		if type (script_name) is bytes:
			script_name = script_name.decode ("utf8")
			
		# return redirect
		if script_name == "":
			if "/" in self.modules:				
				return 1
			else:
				return 0
			
		cands = []
		for route in self.modules:
			if route == "/":
				if script_name == "/":
					return "/"
																	
			else:				
				if script_name == route or script_name.startswith (route [-1] != "/" and route + "/" or route):
					cands.append (route)
					
				elif script_name == route [:-1]:
					return 1
		
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

		

