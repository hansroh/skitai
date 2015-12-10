import re
try:
	from urllib.parse import unquote_plus
except ImportError:
	from urllib import unquote_plus	
import os


RX_RULE = re.compile ("(/<(.+?)>)")

class Package:
	def __init__ (self, env, module = None, packagename = None):
		self.env = env
		self.module = module
		self.packagename = packagename
		self.wasc = None		
		self.logger = None
		self.route_map = {}
		self.packages = {}
		
		self._before_request = None
		self._success_request = None
		self._teardown_request = None
		self._failed_request = None
		self._startup = None
		self._shutdown = None
		self._onreload = None
		
		if self.module:
			self.abspath = self.module.__file__
			if self.abspath [-3:] != ".py":
				self.abspath = self.abspath [:-1]
			self.update_file_info	()
		
	def cleanup (self):
		if self._shutdown:
			self._shutdown (self.wasc, self)
		
	def __getitem__ (self, k):
		return self.route_map [k]
	
	def log (self, msg):
		self.logger.log (msg)
	
	def trace (self):
		self.logger.trace ()
		
	def reload_package (self):
		impoter.reloader (self.module)
		self.update_file_info	()
	
	def is_reloadable (self):
		if self.module is None: return False
		stat = os.stat (self.abspath)
		return self.file_info != (stat.st_mtime, stat.st_size)		
			
	def update_file_info (self):
		stat = os.stat (self.abspath)
		self.file_info = (stat.st_mtime, stat.st_size)
		
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
	
	def success_request (self, f):
		self._success_request = f
	
	def teardown_request (self, f):
		self._teardown_request = f
	
	def failed_request (self, f):
		self._failed_request = f
		
	def route (self, rule, *t, **k):		
		def decorator(f):
			self.add_route (rule, f, *t, **k)
		return decorator
	
	def get_route_map (self):
		return self.route_map
	
	def set_route_map (self, route_map):
		self.route_map = route_map
		
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
	
	def add_package (self, module, packagename):
		p = Package (self.env, module, packagename)
		self.packages [id (p)] = p
	
	def try_rule (self, path_info, rulepack):
		rule, (f, a) = rulepack		
		if type (rule) is type (""): 
			return None, None
			
		arglist = rule.findall (path_info)
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
	
	def route_search (self, path_info):
		if path_info in self.route_map:			
			return self.route_map [path_info][0]
		if path_info [-1] == "/" and path_info [:-1] in self.route_map:
			return path_info [:-1]
		if path_info + "/" in self.route_map:		
			return path_info + "/"
		raise KeyError
					
	def get_package_method (self, path_info, use_reloader = False):
		# 1st, try find in self
		method, kargs, match, matchtype = None, {}, None, 0
		try:			
			method = self.route_map [path_info][0]			
		except KeyError: 
			for rulepack in list(self.route_map.items ()):
				method, kargs = self.try_rule (path_info, rulepack)
				if method: 
					match = rulepack
					break
				matchtype = 2
		else:
			if type (method) is str:
				return method, None, None, 3
			match = path_info
			matchtype = 1
		
		# 2nd, try find in sub packages
		if method is None and self.packages:
			for pid in list (self.packages.keys ()):
				package = self.packages [pid]
				subapp = getattr (package.module, package.packagename)
				if use_reloader and subapp.is_reloadable ():
					del self.packages [pid]
					args, old_p = (package.module, package.packagename), package.packages
					subapp.reload_package ()
					self.add_package (*args)
					p.start (self.wasc, old_p)
					
				method, kargs, match, matchtype = subapp.get_package_method (path_info, use_reloader)
				if method:
					break
			
		if not method:
			return (None, None, None, 0)
																	
		return (
			[
				self._before_request, 
				method, 
				self._success_request, 
				self._failed_request, 
				self._teardown_request
			], 
			kargs, match, matchtype
		)
	
	def start (self, wasc, packages = None):
		self.wasc = wasc
		if self._startup and packages is None:
			# initing app & packages
			if self._startup:
				self._startup (self.wasc, self)
			
			for p in list (self.packages.values ()):
				p.start (self.wasc)
				
		elif packages and	self._onreload:
			self._onreload (self.wasc, self)
			self.packages = packages


