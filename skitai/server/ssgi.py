import threading 
import asyncore
import re
try:
	from urllib.parse import unquote_plus
except ImportError:
	from urllib import unquote_plus	
import time
import os

JINJA2 = True
try:
	from jinja2 import Environment, PackageLoader
except ImportError:
	JINJA2 = False

class vwas: 
	request = {}
	@classmethod
	def registerObj (cls, k, v):
		setattr (cls, k, v)

RX_RULE = re.compile ("(/<(.+?)>)")

class Package:
	def __init__ (self):		
		self.wasc = None
		self.base_route = None
		self.logger = None
		self.route_map = {}
		self.packages = {}
		
		self._before_request = None
		self._after_request = None
		self._teardown_request = None
		self._startup = None
		self._shutdown = None
		self._onreload = None
		
	def cleanup (self):
		if self._shutdown:
			self._shutdown (self.wasc, self)
		
	def __getitem__ (self, k):
		return self.route_map [k]
	
	def log (self, msg):
		self.logger.log (msg)
	
	def trace (self):
		self.logger.trace ()
	
	def set_devel (self, flag = True):
		self.devel_mode = flag
		self.set_auto_reload (flag)
		for module in list(self.packages.keys ()):
			module.package.set_devel (flag)
		
	def is_devel (self):
		return self.devel_mode
				
	def set_auto_reload (self, flag = True):
		self.auto_reload = flag
	
	def do_auto_reload (self):
		return self.auto_reload
		
	def add_route (self, rule, func, *t, **k):
		s = rule.find ("/<")
		if s == -1:	
			self.route_map [rule] = (func, None)
		else:
			rulenames = []
			for r, n in RX_RULE.findall (rule):
				rulenames.append (n)
				if n.startswith ("int:"):
					rule = rule.replace (r, "/([0-9]+)")
				elif n.startswith ("float:"):
					rule = rule.replace (r, "/([\.0-9]+)")
				elif n.startswith ("path:"):
					rule = rule.replace (r, "/(.+)")	
				else:
					rule = rule.replace (r, "/([^/]+)")
			rule = rule.replace (".", "\.") + "$"
			re_rule = re.compile (rule)				
			self.route_map [re_rule] = (func, tuple (rulenames))
	
	def onreload (self, f):
		self._onreload = f
		
	def startup (self, f):
		self._startup = f
	
	def shutdown (self, f):
		self._shutdown = f
		
	def before_request (self, f):
		self._before_request = f
	
	def after_request (self, f):
		self._after_request = f
	
	def teardown_request (self, f):
		self._teardown_request = f
	
	def route (self, rule, *t, **k):		
		def decorator(f):
			self.add_route (rule, f, *t, **k)
		return decorator
	
	def get_route_map (self):
		return self.route_map
	
	def set_route_map (self, route_map):
		self.route_map = route_map
		
	def set_base_route (self, base):
		self.base_route = base
	
	def get_base_route (self):
		return self.base_route
			
	def absurl (self, f):
		if not f:
			return self.base_route						
		if self.base_route [-1] == "/":
			if f [0] == "/":
				return self.base_route + f [1:]
		else:
			if f [0] != "/":
				return self.base_route + "/" + f					
		return self.base_route + f
	
	def add_package (self, module, packages = None):
		fn = module.__file__
		if fn [-1] == "c": fn = fn [:-1]
		module.package.set_auto_reload (self.do_auto_reload ())
		module.package.run (self.wasc, self.get_base_route (), packages)
		self.packages [module] = (os.path.getmtime (fn), os.path.getsize (fn))
				
	def reload_package (self, module):
		module.package.cleanup ()
		subpackages = module.package.packages
		del self.packages [module]
		reload (module)
		self.add_package (module, subpackages)
	
	def try_rule (self, uri, rulepack):
		rule, (f, a) = rulepack		
		if type (rule) is type (""): 
			return None, None
			
		arglist = rule.findall (uri)
		if not arglist: 
			return None, None

		arglist = arglist [0]
		kargs = {}
		for i in range(len(arglist)):
			if a [i].startswith ("int:"):
				kargs [a[i][4:]] = int (arglist [i])
			elif a [i].startswith ("float:"):		
				kargs [a[i][6:]] = float (arglist [i])
			elif a [i].startswith ("path:"):		
				kargs [a[i][5:]] = unquote_plus (arglist [i])
			else:		
				kargs [a[i]] = unquote_plus (arglist [i]).replace ("_", " ")
						
		return f, kargs
	
	def check_reload (self):		
		for module, (mtime, size) in list(self.packages.items ()):
			fn = module.__file__
			if fn [-1] == "c": fn = fn [:-1]				
			if mtime != os.path.getmtime (fn) or size != os.path.getsize (fn):
					self.reload_package (module)
					
	def get_package_method (self, uri):
		method, kargs, match, matchtype = None, {}, None, 0
		if uri == "": 
			uri = "/"
		
		if self.do_auto_reload ():
			self.check_reload ()
			
		try:			
			method = self.route_map [uri][0]
		except KeyError: 
			for rulepack in list(self.route_map.items ()):
				method, kargs = self.try_rule (uri, rulepack)
				if method: 
					match = rulepack
					break
				matchtype = 2
		else:
			match = uri
			matchtype = 1
										
		if method is None and self.packages:
			for module, (mtime, size) in list(self.packages.items ()):
				method, kargs, match, matchtype = module.package.get_package_method (uri)				
				if method:
					break
			
		if not method:
			return (None, None, None, 0)
																	
		return ([self._before_request, method, self._after_request, self._teardown_request], kargs, match, matchtype)
	
	def run (self, wasc, base_route, packages = None):
		self.wasc = wasc
		self.set_base_route (base_route)
		self.logger = self.wasc.logger.get ("app")
		if packages:
			self.packages = packages
			if self._onreload:
				self._onreload (self.wasc, self)
																
		else:
			for module in list(self.packages.keys ()):
				module.package.run (self.wasc, self.get_base_route ())
			if self._startup:
				self._startup (self.wasc, self)
				
		
class Application (Package):
	auto_reload = False
	devel_mode = False
	enable_session = False
	permission = []
	
	def __init__ (self, package_name):
		Package.__init__ (self)
		if JINJA2:
			self.env = Environment (loader = PackageLoader (package_name))
		self.lock = threading.RLock ()
		self.cache_sorted = 0
		self.cached_paths = {}
		self.cached_rules = []
	
	def set_devel (self, flag = True):
		Package.set_devel (self, flag)
		if flag == True:
			self.lock.acquire ()
			self.cached_paths = {}
			self.cached_rules = []
			self.lock.release ()
	
	def get_template (self, name):
		if JINJA2:
			return self.env.get_template(name)
		raise ImportError ("jinja2 required.")
		
	def get_lock (self):
		return self.lock
	
	def permit_to (self, group):
		self.permission.append (group)
	
	def get_permission (self):
		return self.permission
	
	def use_session (self, flag = True):
		self.enable_session = flag
	
	def is_session_enabled (self):
		return self.enable_session
		
	def get_method (self, uri):
		method, kargs = None, {}
		self.lock.acquire ()
		try:
			method = self.cached_paths [uri]
		except KeyError:
			for rulepack, freg in self.cached_rules:
				method, kargs = self.try_rule (uri, rulepack)
				if method: 
					break
		finally:
			self.lock.release ()
	
		if not method:
			if self.do_auto_reload ():
				self.lock.acquire ()																
			try:	
				method, kargs, match, matchtype = self.get_package_method (uri)
			finally:	
				if self.do_auto_reload (): 
					self.lock.release ()
			
			if not self.do_auto_reload ():
				self.lock.acquire ()
				if matchtype == 1:
					self.cached_paths [match] = method				
				elif matchtype == 2:
					self.cached_rules.append ([match, 1])
					if time.time () - self.cache_sorted > 300:
						self.cached_rules.sort (lambda x, y: cmp (y[1], x[1]))
						self.cached_rules.sort (key = lambda x: x[1], reverse = True)
						self.cache_sorted = time.time ()			
				self.lock.release ()
				
		return method, kargs
		
