from . import default_handler, wsgi_handler, proxypass_handler, websocket_handler, api_access_handler
import skitai
if skitai.HTTP2:
	from . import http2_handler		
from .. import wsgi_apps
import os

class VHost:
	def __init__ (self, wasc, clusters, cachefs, static_max_age, apigateway_authenticate, apigateway_realm):
		self.wasc = wasc
		self.clusters = clusters
		self.cachefs = cachefs
		
		self.apps = wsgi_apps.ModuleManager(self.wasc, self)
		self.proxypass_handler = proxypass_handler.Handler (self.wasc, clusters, cachefs)
		if apigateway_authenticate:
			self.access_handler = api_access_handler.Handler (self.wasc, apigateway_realm, self.proxypass_handler)
			self.handlers = [self.access_handler]
		else:
			self.access_handler = None
			self.handlers = [self.proxypass_handler]
						
		alternative_handlers = [			
			websocket_handler.Handler (self.wasc, self.apps),
			wsgi_handler.Handler (self.wasc, self.apps)
		]
		if skitai.HTTP2:
			alternative_handlers.insert (0, http2_handler.Handler (self.wasc, self.apps))
			
		self.default_handler = default_handler.Handler (self.wasc, {}, static_max_age, alternative_handlers)		
		self.handlers.append (self.default_handler)
	
	def close (self):	
		for h in self.handlers:
			try: h.close ()
			except AttributeError: pass		
		self.apps.cleanup ()
	
	def set_token_storage (self, storage):
		if self.access_handler:
			self.access_handler.set_token_storage (storage)
						
	def add_proxypass (self, route, cname):
		self.proxypass_handler.add_route (route, cname)
		
	def add_route (self, route, target):
		self.default_handler.add_route (route, target)		
		
	def add_module (self, route, path, module):
		self.apps.add_module (route, path, module)


class Handler:
	def __init__ (self, wasc, clusters, cachefs, static_max_age, apigateway_authenticate, apigateway_realm):
		self.wasc = wasc
		self.vhost_args = (clusters, cachefs, static_max_age, apigateway_authenticate, apigateway_realm)		
		self.sites = {}
		self.__cache = {}
	
	def close (self):	
		for v in self.sites.values ():
			if hasattr (v, "close"):
				v.close ()
				
	def match (self, request):
		return self.find (request.get_header ("host")) and 1 or 0
		
	def handle_request (self, request):
		vhost = self.find (request.get_header ("host"))
		for h in vhost.handlers:
			if h.match (request):
				h.handle_request (request)
				break
			
	def add_route (self, rule, routepair):
		if rule.strip () in ("*", "default"):
			rule = None
		else:
			rule = tuple (rule.split ())
		
		if rule not in self.sites:				
			self.sites [rule] = VHost (self.wasc, *self.vhost_args)

		vhost = self.sites [rule]
		route, target = [x.strip () for x in routepair.split ("=", 1)]
		if target.startswith ("@"):
			if route [-1] == "/":
				route = route [:-1]
			vhost.add_proxypass (route, target [1:].strip ())
		
		elif os.path.isdir (target):
			if route [-1] == "/":
				route = route [:-1]
			vhost.add_route (route, target)
			
		else:
			fullpath = os.path.split (target.strip())
			vhost.add_module (route, os.sep.join (fullpath[:-1]), fullpath [-1])
		
	def find (self, host):
		if host:
			host = host.split (":", 1)[0]
			vhost = self.__cache.get (host)
			if vhost:
				return vhost
				
			for rules in self.sites:
				if rules is None: continue
				if host in rules:
					vhost = self.sites [rules]
					self.__cache [host] = vhost
					return vhost
					
				for rule in rules:
					if rule [0] == "." and host.endswith (rule) or host == rule [1:]:
						vhost = self.sites [rules]
						self.__cache [host] = vhost
						return vhost
						
		return self.sites.get (None, None)
	
	