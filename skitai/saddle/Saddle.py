import threading 
import time
import os
import sys
from . import package, multipart_collector
from . import wsgi_executor, xmlrpc_executor
from skitai.server import producers
from skitai.server.threads import trigger


try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
	
JINJA2 = True
try:
	from jinja2 import Environment, PackageLoader
except ImportError:
	JINJA2 = False

class Saddle (package.Package):
	use_reloader = False
	debug = False
	
	def __init__ (self, package_name):
		self.template_env = JINJA2 and Environment (loader = PackageLoader (package_name)) or None
		package.Package.__init__ (self)	
		self.lock = threading.RLock ()
		self.cache_sorted = 0
		self.cached_paths = {}
		self.cached_rules = []
	
	def set_devel (self, debug = True, use_reloader = True):
		self.debug = debug
		self.use_reloader = use_reloader
	
	def get_template (self, name):
		if JINJA2:
			return self.template_env.get_template (name)
		raise ImportError ("jinja2 required.")
	
	def get_multipart_collector (self):
		return multipart_collector.MultipartCollector
	
	def get_method (self, path_info):
		method, kargs = None, {}
		self.lock.acquire ()
		try:
			method = self.cached_paths [path_info]
		except KeyError:
			for rulepack, freg in self.cached_rules:
				method, kargs = self.try_rule (path_info, rulepack)
				if method: 
					break
		finally:
			self.lock.release ()
	
		if not method:
			if self.use_reloader:
				self.lock.acquire ()																
			try:	
				method, kargs, match, matchtype = self.get_package_method (path_info, self.use_reloader)
			finally:	
				if self.use_reloader: 
					self.lock.release ()
			
			if not self.use_reloader:
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
					
			if matchtype == 3:
				return method, 301
		
		return method, kargs
	
	def restart (self, wasc, route):
		self.wasc = wasc
		self.route = route
		if self._onreload:
			self._onreload (self.wasc, self)		
							
	def __call__ (self, env, start_response):
		env ["skitai.was"].app = self
		env ["skitai.was"].ab = self.build_url
		content_type = env.get ("CONTENT_TYPE", "")				
		if content_type.startswith ("text/xml") or content_type.startswith ("application/xml+rpc"):
			return xmlrpc_executor.Executor (env, self.get_method) ()
		else:	
			return wsgi_executor.Executor (env, self.get_method) ()		
			
	