import threading 
import time
import os
import sys
from . import part, multipart_collector, cookie, session
from . import wsgi_executor, xmlrpc_executor
from skitai.lib import producers
from skitai.server import utility
from hashlib import md5
import random
import base64
from skitai.saddle import cookie
JINJA2 = True
try:	
	from jinja2 import Environment, PackageLoader
except ImportError:
	JINJA2 = False
		
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib


class Config:
	max_post_body_size = 5 * 1024 * 1024
	max_cache_size = 5 * 1024 * 1024
	max_multipart_body_size = 20 * 1024 * 1024
	max_upload_file_size = 20000000


class AuthorizedUser:
	def __init__ (self, user, realm, info = None):
		self.name = user
		self.realm = realm
		self.info = info
		
				
class Saddle (part.Part):
	use_reloader = False
	debug = False
	
	# Session
	securekey = None
	session_timeout = None
	
	#WWW-Authenticate
	authenticate = False
	authorization = "digest"	
	realm = None
	users = {}	
	opaque = None	
	
	def __init__ (self, app_name):
		part.Part.__init__ (self)
		self.app_name = app_name
		self.jinja_env = JINJA2 and Environment (loader = PackageLoader (app_name)) or None		
		self.lock = threading.RLock ()
		self.cache_sorted = 0
		self.cached_paths = {}
		self.cached_rules = []
		self.config = Config ()
	
	def jinja_overlay (self, line_statement = "%", variable_string = "#", block_start_string = "{%", block_end_string = "}", **karg):
		from . import jinjapatch
				
		self.jinja_env = jinjapatch.Environment (
			loader = PackageLoader (self.app_name),
		  variable_start_string=variable_string,
		  variable_end_string=variable_string,
		  line_statement_prefix=line_statement,
		  block_end_string = block_end_string,
		  block_start_string = block_start_string,
		  line_comment_prefix=line_statement * 2,
		  trim_blocks = True,
			lstrip_blocks = True,
		  **karg
		)
	
	def render (self, was, template_file, _do_not_use_this_variable_name_ = {}, **karg):
		while template_file and template_file [0] == "/":
			template_file = template_file [1:]	
											
		if _do_not_use_this_variable_name_: 
			assert not karg, "Can't Use Dictionary and Keyword Args Both"
			karg = _do_not_use_this_variable_name_

		karg ["was"] = was		
		template = self.get_template (template_file)
		self.when_got_template (was, template, karg)
			
		rendered = template.render (karg)
		self.when_template_rendered (was, template, karg, rendered)
		return rendered	
					
	def get_template (self, name):
		if JINJA2:
			return self.jinja_env.get_template (name)
		raise ImportError ("jinja2 required.")
			
	def get_www_authenticate (self):
		if self.authorization == "basic":
			return 'Basic realm="%s"' % self.realm
		else:	
			if self.opaque is None:
				self.opaque = md5 (self.realm.encode ("utf8")).hexdigest ()
			return 'Digest realm="%s", qop="auth", nonce="%s", opaque="%s"' % (
				self.realm, utility.md5uniqid (), self.opaque
			)
	
	def get_password (self, user):
		info = self.users.get (user)
		if not info:
			return None, 0 # passwrod, encrypted
		return type (info) is str and (info, 0) or info [:2]
	
	def get_info (self, user):
		info = self.users.get (user)
		if not info: return None
		return (type (info) is not str and len (info) == 3) and info [-1] or None
				
	def authorize (self, auth, method, uri):
		if self.realm is None or not self.users:
			return
				
		if auth is None:
			return self.get_www_authenticate ()
		
		# check validate: https://evertpot.com/223/
		amethod, authinfo = auth.split (" ", 1)
		if amethod.lower () != self.authorization:
			return self.get_www_authenticate ()
		
		if self.authorization == "basic":
			basic = base64.decodestring (authinfo.encode ("utf8")).decode ("utf8")
			current_user, current_password = basic.split (":", 1)
			password, encrypted = self.get_password (current_user)
			if encrypted:
				raise AssertionError ("Basic authorization can't handle encrypted password")
			if password ==  current_password:
				return AuthorizedUser (current_user, self.realm, self.get_info (current_user))
				
		else:
			method = method.upper ()
			infod = {}
			for info in authinfo.split (","):
				k, v = info.strip ().split ("=", 1)
				if not v: return self.get_www_authenticate ()
				if v[0] == '"': v = v [1:-1]
				infod [k]	 = v
			
			current_user = infod.get ("username")
			if not current_user:
				return self.get_www_authenticate ()
			
			password, encrypted = self.get_password (current_user)
			if not password:
				return self.get_www_authenticate ()
				
			try:
				if uri != infod ["uri"]:					
					return self.get_www_authenticate ()
				if encrypted:	
					A1 = password
				else:
					A1 = md5 (("%s:%s:%s" % (infod ["username"], self.realm, password)).encode ("utf8")).hexdigest ()
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
					return AuthorizedUser (current_user, self.realm, self.get_info (current_user))
					
			except KeyError:
				pass
		
		return self.get_www_authenticate ()
			
	def set_devel (self, debug = True, use_reloader = True):
		self.debug = debug
		self.use_reloader = use_reloader
	
	def get_multipart_collector (self):
		return multipart_collector.MultipartCollector
	
	def get_method (self, path_info, command = None, content_type = None, authorization = None):		
		current_app, method = self, None
		
		with self.lock:
			try:
				method, options = self.cached_paths [path_info]
			except KeyError:
				ind = 0
				for rulepack, freg, options in self.cached_rules:
					method, kargs = self.try_rule (path_info, rulepack)
					if method:						
						self.cached_rules [ind][1] += 1
						break
					ind += 1					
								
		if not method:
			if self.use_reloader:
				self.lock.acquire ()																
			try:	
				current_app, method, kargs, options, match, matchtype = self.get_package_method (path_info, command, content_type, authorization, self.use_reloader)
			finally:	
				if self.use_reloader: 
					self.lock.release ()
			
			if matchtype == -1:
				return current_app, method, None, 301
			
			if not method:
				return current_app, None, None, 404
				
			if not self.use_reloader:
				if matchtype == 1:
					with self.lock:
						self.cached_paths [match] = (method, options)
								
				elif matchtype == 2:
					with self.lock:
						self.cached_rules.append ([match, 1, options])
						if time.time () - self.cache_sorted > 300:
							self.cached_rules.sort (key = lambda x: x[1], reverse = True)
							self.cache_sorted = time.time ()
		
		resp_code = 0
		if options:
			allowed = options.get ("methods", [])
			if allowed and command not in allowed:
				return current_app, None, None, 405 # method not allowed		
			allowed = options.get ("content_types", [])	
			if allowed and content_type not in allowed:
				return current_app, None, None, 415 # unsupported media type
			resp_code = options.get ("authenticate", False) and 401 or 0
									
		return current_app, method, kargs, resp_code			
	
	def restart (self, wasc, route):
		self.start (wasc, route, self.packages)
	
	def create_on_demand (self, was, name):
		class G: 
			pass
		
		# create just in time objects
		if name == "cookie":
			return cookie.Cookie (was.request, self.securekey, self.route [:-1], self.session_timeout)
			
		elif name in ("session", "mbox"):
			if not was.in__dict__ ("cookie"):
				was.cookie = cookie.Cookie (was.request, self.securekey, self.route [:-1], self.session_timeout)			
			if name == "session":
				return was.cookie.get_session ()
			if name == "mbox":
				return was.cookie.get_notices ()
				
		elif name == "g":
			return G ()
		
	def cleanup_on_demands (self, was):
		if was.in__dict__ ("g"):
			del was.g
		if not was.in__dict__ ("cookie"):
			return
		for j in ("session", "mbox"):
			if was.in__dict__ (j):		
				delattr (was, j)
		del was.cookie
										
	def __call__ (self, env, start_response):
		was = env ["skitai.was"]		
		was.app = self
		was.ab = self.build_url
		was.response = was.request.response
		
		content_type = env.get ("CONTENT_TYPE", "")				
		if content_type.startswith ("text/xml") or content_type.startswith ("application/xml+rpc"):
			result = xmlrpc_executor.Executor (env, self.get_method) ()
		else:	
			result = wsgi_executor.Executor (env, self.get_method) ()		
		
		del was.response
		del was.ab		
		self.cleanup_on_demands (was) # del session, mbox, cookie, g
			
		return result
		