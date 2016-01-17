import threading 
import time
import os
import sys
from . import package, multipart_collector, cookie
from . import wsgi_executor, xmlrpc_executor
from skitai.lib import producers
from skitai.server import utility
from hashlib import md5
import random
import base64


try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
	
JINJA2 = True
try:
	from jinja2 import Environment, PackageLoader
except ImportError:
	JINJA2 = False

multipart_collector.MultipartCollector.file_max_size = 20 * 1024 * 1024
multipart_collector.MultipartCollector.cache_max_size = 5 * 1024 * 1024
cookie.SecuredCookieValue.default_session_timeout = 1200

	
class Saddle (package.Package):
	use_reloader = False
	debug = False
	
	# Session
	securekey = None
	session_timeout = None
	
	#WWW-Authenticate
	authorization = "digest"
	realm = None
	user = None
	password = None
	
	opaque = None
	
	def __init__ (self, package_name):
		self.template_env = JINJA2 and Environment (loader = PackageLoader (package_name)) or None
		package.Package.__init__ (self)	
		self.lock = threading.RLock ()
		self.cache_sorted = 0
		self.cached_paths = {}
		self.cached_rules = []
		
	def __setattr__ (self, name, attr):
		if name == "upload_file_max_size":
			multipart_collector.MultipartCollector.file_max_size = attr
		self.__dict__ [name] = attr
	
	def get_www_authenticate (self):
		if self.authorization == "basic":
			return 'Basic realm="%s"' % self.realm
		else:	
			if self.opaque is None:
				self.opaque = md5 (self.realm.encode ("utf8")).hexdigest ()
			return 'Digest realm="%s", qop="auth", nonce="%s", opaque="%s"' % (
				self.realm, utility.md5uniqid (), self.opaque
			)
			
	def authorize (self, auth, method, uri):
		if self.realm is None or self.user is None or self.password is None:
			return		
		if auth is None:
			return self.get_www_authenticate ()
		
		# check validate: https://evertpot.com/223/
		amethod, authinfo = auth.split (" ", 1)
		if amethod.lower () != self.authorization:
			return self.get_www_authenticate ()
			
		if self.authorization == "basic":
			basic = base64.decodestring (authinfo.encode ("utf8"))
			if basic == "%s:%s" % (self.username, self.password):
				return
				
		else:
			method = method.upper ()
			infod = {}
			for info in authinfo.split (","):
				k, v = info.strip ().split ("=", 1)
				if not v: return self.get_www_authenticate ()
				if v[0] == '"': v = v [1:-1]
				infod [k]	 = v
			
			try:
				if uri != infod ["uri"]:					
					return self.get_www_authenticate ()
				A1 = md5 (("%s:%s:%s" % (self.user, self.realm, self.password)).encode ("utf8")).hexdigest ()
				A2 = md5 (("%s:%s" % (method, infod ["uri"])).encode ("utf8")).hexdigest ()
				Hash = md5 (("%s:%s:%s:%s:%s:%s" % (
					A1, 
					infod ["nonce"],
					infod ["nc"],
					infod ["cnonce"],
					infod ["qop"],
					A2
					)).encode ("utf8")
				).hexdigest ()

				if Hash == infod ["response"]:				
					return
					
			except KeyError:
				pass
		
		return self.get_www_authenticate ()
			
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
		was = env ["skitai.was"]		
		was.app = self
		was.ab = self.build_url
		
		content_type = env.get ("CONTENT_TYPE", "")				
		if content_type.startswith ("text/xml") or content_type.startswith ("application/xml+rpc"):
			result = xmlrpc_executor.Executor (env, self.get_method) ()
		else:	
			result = wsgi_executor.Executor (env, self.get_method) ()		
		
		was.cookie = None
		was.session = None
		was.response = None
		was.env = None
		was.app = None
		was.ab = None
		was.temp = None		
		
		return result
		