import threading 
import time
import os
import sys
from skitai.server  import utility, http_cookie
from skitai.lib.reraise import reraise 
from . import package

JINJA2 = True
try:
	from jinja2 import Environment, PackageLoader
except ImportError:
	JINJA2 = False


class Saddle (package.Package):
	use_reloader = False
	debug = False
	
	def __init__ (self, package_name):
		env = JINJA2 and Environment (loader = PackageLoader (package_name)) or None
		package.Package.__init__ (self, env, None, None)	
		self.lock = threading.RLock ()
		self.cache_sorted = 0
		self.cached_paths = {}
		self.cached_rules = []
	
	def set_devel (self, debug = True, use_reloader = True):
		self.debug = debug
		self.use_reloader = use_reloader
	
	def get_template (self, name):
		if JINJA2:
			return self.env.get_template(name)
		raise ImportError ("jinja2 required.")
	
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
				method, kargs, match, matchtype = self.get_package_method (path_info)
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
				elif matchtype == 3:
					return method, 301													
				self.lock.release ()
		
		return method, kargs
	
	def chained_exec (self, was, method, args):
		# recursive before, after, teardown
		# [b, [b, [b, func, s, f, t], s, f, t], s, f, t]
		
		response = None
		exc_info = None
		
		[before, func, success, failed, teardown] = method
		
		try:
			if before:
				response = before (was)
				if response:
					return response
			
			if type (func) is list:
				response = self.chained_exec (was, func, args)					
					
			else:
				response = func (was, **args)
				
		except MemoryError:
			raise
																										
		except Exception as expt:
			was.logger.trace ("app")
			exc_info = sys.exc_info ()
			if failed:
				try:
					failed (was)		
				except:
					was.logger.trace ("app")
					exc_info = sys.exc_info ()
			
		else:
			if success: 
				try:
					success (was)
				except:
					was.logger.trace ("app")
					exc_info = sys.exc_info ()
		
		if teardown:
			try:
				response = teardown (was)
			except:
				was.logger.trace ("app")
				exc_info = sys.exc_info ()
		
		if exc_info:
			reraise (*exc_info)
		
		return response
		
	def commit (self, was):
		# keep commit order, session -> cookie
		try: was.session.commit ()
		except AttributeError: pass							
		was.cookie.commit ()
	
	def merge_args (self, s, n):
		for k, v in list(n.items ()):
			if k in s:
				if type (s [k]) is not list:
					s [k] = [s [k]]
				s [k].append (v)
			else:	 
				s [k] = v
		
	def parse_args (self, env, args):
		allargs = {}
		query = env.get ("QUERY_STRING")
		data = None
		_input = env ["wsgi.input"]		
		if _input:
			if type (_input) is dict:
				self.merge_args (allargs, args)				
			else:				
				data = _input.read ()
			
		if query: 
			self.merge_args (allargs, utility.crack_query (query))			
		if data:
			self.merge_args (allargs, utility.crack_query (data))			
		
		return allargs
	
	def generate_content (self, env, method, kargs):
		_kargs = self.parse_args (env, kargs)
		_was = env.get ("wsgi.x_was")
		if _was:
			_was.response = _was.request.response
			_was.cookie = http_cookie.Cookie (_was.request)
			_was.session = _was.cookie.get_session ()
		
		response = self.chained_exec (_was, method, _kargs)
		self.commit (_was)
		return response
					
	def __call__ (self, env, start_response):
		method, kargs = self.get_method (env ["PATH_INFO"])
		if method is None:
			start_response ("404 Not Found", [])
			return None
		if kargs == 301:
			start_response ("301 Moved Permanently", [("Location", method)])
			return None
		return self.generate_content (env, method, kargs)
			
