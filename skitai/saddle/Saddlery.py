import re, sys
from functools import wraps
from urllib.parse import unquote_plus, quote_plus, urljoin
import os
from aquests.lib import importer, strutil
from types import FunctionType as function
import inspect
from . import part
			
RX_RULE = re.compile ("(/<(.+?)>)")

class Saddlery (part.Part):
	def __init__ (self, *args, **kargs):
		part.Part.__init__ (self, *args, **kargs)
		self.packages = {}
		
	def mount (self, mount, module, partname = "app"):
		part = getattr (module, partname)
		part.init (module, partname, self.mount_p [:-1] + mount)
		self.packages [id (part)] = part
	
	def get_package_method (self, path_info, command, content_type, authorization, use_reloader = False):		
		app, method, kargs, options, match, matchtype = part.Part.get_package_method (
			self, path_info, command, content_type, authorization, use_reloader
		)
		
		if method is None and self.packages:
			for pid in list (self.packages.keys ()):
				package = self.packages [pid]
				subapp = getattr (package.module, package.packagename)
								
				if use_reloader and subapp.is_reloadable ():
					del self.packages [pid]
					args, its_packages = (package.mount_p, package.module, package.packagename), package.packages
					subapp.reload_package ()
					self.mount (*args)
					package.start (self.wasc, self.route, its_packages)
					subapp = getattr (package.module, package.packagename)
										
				app, method, kargs, options, match, matchtype = subapp.get_package_method (path_info, method, content_type, authorization, use_reloader)				
				if method:
					break
		
		if method is None:
			return None, None, None, None, None, 0
		
		if matchtype == -1: # 301 move
			return app, method, None, None, None, -1
			
		return app, [self._binds_request [0], method] + self._binds_request [1:4], kargs, options, match, matchtype
	
	def build_url (self, thing, *args, **kargs):
		url = part.Part.build_url (self, thing, *args, **kargs)
		if url is None:
			for p in self.packages:
				url = self.packages [p].build_url (thing, *args, **kargs)
				if url:
					return url
	
	def cleanup (self):
		# initing app & packages		
		self._binds_server [2] and self._binds_server [2] (self.wasc)
		for p in list (self.packages.values ()):
			p.cleanup ()
			
	def start (self, wasc, route, packages = None):
		self.wasc = wasc
		if not route: 
			self.route = "/"
		elif not route.endswith ("/"):			
			self.route = route + "/"
		else:
			self.route = route
			
		if packages is None:
			# initing app & packages
			self._binds_server [0] and self._binds_server [0] (self.wasc)
			for p in list (self.packages.values ()):
				p.start (self.wasc, route)
				
		else:
			self._binds_server [1] and self._binds_server [1] (self.wasc)
			self.packages = packages

	def restart (self, wasc, route):
		self.start (wasc, route, self.packages)
		