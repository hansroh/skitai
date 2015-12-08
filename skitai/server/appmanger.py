import os, sys, re, types
from skitai.lib  import pathtool
import threading
import importlib
try: reloader = importlib.reload
except AttributeError: reloader = reload	

RXFUNC = re.compile (r"^def\s+([_a-z][_a-z0-9]*)\s*(\(.+?\))\s*:", re.I|re.M|re.S)

class Module:
	def __init__ (self, wasc, route, libpath):
		self.route = route
		if self.route [-1] == "/":
			self.rm_len = len (self.route) - 1
		else:
			self.rm_len = len (self.route)	
			
		self.libpath = libpath
		self.wasc = wasc
		self.import_app ()		
		self.start_application ()
	
	def import_app (self):
		__import__ (self.libpath, globals ())
		self.libpath, self.abspath = pathtool.modpath (self.libpath)
		self.module = sys.modules [self.libpath]
		self.app = self.module.app
		
		if self.abspath [-4:] in (".pyc", ".pyo"):
			self.abspath = self.abspath [:-1]		
		self.update_file_info ()
		
	def reload_app (self):
		reloader (self.module)
		self.reload_application ()				
		self.update_file_info ()
		
	def update_file_info (self):
		stat = os.stat (self.abspath)
		self.size_file, self.last_modified = stat.st_size, stat.st_mtime	
	
	def ischanged (self):
		stat = os.stat (self.abspath)
		return stat.st_size != self.size_file or stat.st_mtime != self.last_modified
	
	def reload_application (self):
		# save packages before reload
		packages = self.app.packages
		try:
			self.app.cleanup ()
		except:
			self.wasc.logger.trace ("app")			
		del self.app
		self.app = self.module.app # new app
		self.start_application (packages)
		
	def start_application (self, packages = None):
		if "sandbox" in self.abspath.split (os.sep):
			self.app.set_devel (True)
		self.app.run (self.wasc, self.get_route (), packages)	
	
	def set_route (self, route):
		route = route
		if not route or route [0] != "/":
			raise TypeError("route url must be abs path")
		while route and route [-1] == "/":
			route = route [:-1]
		self.route = route
		self.route_len = len (route)
		
	def get_route (self):
		return self.route
	
	def get_admin_links (self):
		return self.app.get_admin_links ()
		
	def get_app (self, script_name):
		if self.app.do_auto_reload () and self.ischanged ():
			self.reload_app ()
		if script_name [0] != "/":
			script_name = "/" + script_name
					
		#remove base path	
		return self.app.get_method (script_name [self.rm_len:]), self.app
		
		
class ModuleManager:
	modules = {}	
	def __init__(self, wasc):
		self.wasc = wasc		
		self.modules = {}
		self.admin_links = {}
		self.pathes_added = {}
	
	def add_path (self, path):
		if path in self.pathes_added: return
		self.pathes_added [path] = None
		sys.path.insert(0, path)
			
	def register_module (self, route, libpath):
		if not route:
			route = "/"

		try: 
			module = Module (self.wasc, route, libpath)			
		except: 
			self.wasc.logger.trace ("app")
			self.wasc.logger ("app", "[error] application load failed: %s" % libpath)
			
		else: 
			route = module.get_route ()
			self.wasc.logger ("app", "[info] application %s imported." % route)
			if route in self.modules:
				self.wasc.logger ("app", "[info] application route collision detected: %s at %s <-> %s" % (route, module.abspath, self.modules [route].abspath), "warn")
			self.modules [route] = module
			
	def add_module (self, route, directory, package = ""):
		self.add_path (directory)
		self.register_module (route, package)
	
	def get_app (self, script_name, rootmatch = False):
		if not rootmatch:
			route = self.has_route (script_name)
			if route in (0, -1):
				return None, None
		else:
			route = "/"
		
		try:	
			method, app = self.modules [route].get_app (script_name)
		except KeyError:
			return None, None
		if method [0]: # == (method, karg), app
			return method, app
		
		return None, None		
		
	def has_route (self, script_name):
		if type (script_name) is bytes:
			script_name = script_name.decode ("utf8")
			
		# return redirect
		if script_name == "":
			if "/" in self.modules:				
				return -1
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
						return -1
		
		if cands:
			if len (cands) == 1:
				return cands [0]
			cands.sort (key = lambda x: len (x))
			return cands [-1]
		elif "/" in self.modules and self.get_app (script_name, True) [0] is not None:
			return "/"
						
		return 0	
	
	def unload (self, route):
		module = self.modules [route]
		self.wasc.logger ("app", "[info] unloading app: %s" % route)
		try: 
			self.wasc.logger ("app", "[info] ..cleanup app: %s" % route)
			module.application.cleanup ()
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
				module.application.cleanup ()
			except AttributeError:
				pass
			except:
				self.wasc.logger.trace ("app")			
	
	def get_admin_pages (self):
		return self.admin_links		
	
	def status (self):
		d = {}
		for path, module in list(self.modules.items ()):
			d ['<a href="%s">%s</a>' % (path, path)] = module.abspath
		return d

		
