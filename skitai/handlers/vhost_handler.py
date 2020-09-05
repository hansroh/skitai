import skitai
from ..wastuff import wsgi_apps
import os

class VHost:
	def __init__ (self, wasc, clusters, cachefs, static_max_ages, enable_apigateway = False, apigateway_authenticate = False, apigateway_realm = "API Gateway", apigateway_secret_key = None):
		from . import default_handler, wsgi_handler, proxypass_handler, websocket_handler, api_access_handler
		from . import http2_handler

		self.wasc = wasc
		self.clusters = clusters
		self.cachefs = cachefs

		self.apps = wsgi_apps.ModuleManager(self.wasc, self)
		self.handlers = []

		self.proxypass_handler = proxypass_handler.Handler (self.wasc, clusters, cachefs)
		if enable_apigateway:
			self.access_handler = api_access_handler.Handler (self.wasc, apigateway_authenticate, apigateway_realm, self.proxypass_handler, apigateway_secret_key)
			alternative_handlers = [self.access_handler]
		else:
			self.access_handler = None
			alternative_handlers = [self.proxypass_handler]
		alternative_handlers.append (websocket_handler.Handler (self.wasc, self.apps))
		self.wsgi_handler = wsgi_handler.Handler (self.wasc, self.apps)
		alternative_handlers.append (self.wsgi_handler)
		self.default_handler = default_handler.Handler (self.wasc, {}, static_max_ages, alternative_handlers)
		self.wsgi_handler.set_static_files (self.default_handler.get_static_files ())

		if self.wasc.httpserver.altsvc:
			from . import http3_handler
			self.handlers.append (http3_handler.Handler (self.wasc, self.default_handler))
		self.handlers.append (http2_handler.Handler (self.wasc, self.default_handler))

	def close (self):
		for h in self.handlers:
			try: h.close ()
			except AttributeError: pass
		self.apps.cleanup ()

	def set_auth_handler (self, storage):
		if self.access_handler:
			self.access_handler.set_auth_handler (storage)

	def add_proxypass (self, route, cname):
		self.proxypass_handler.add_route (route, cname)

	def add_route (self, route, target):
		self.default_handler.add_route (route, target)

	def add_module (self, route, path, module, pref, name):
		self.apps.add_module (route, path, module, pref, name)


class Handler:
	def __init__ (self, wasc, *args):
		self.wasc = wasc
		self.vhost_args = args
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

	def get_vhost (self, rule):
		if rule.strip () in ("*", "default"):
			rule = None
		else:
			rule = tuple (rule.split ())
		if rule not in self.sites:
			self.sites [rule] = VHost (self.wasc, *self.vhost_args)
		return self.sites [rule]

	def add_app (self, rule, route, app, root, config = None, name = None):
		# app object mount, maily used by unittest
		vhost = self.get_vhost (rule)
		vhost.add_module (route, root, app, config, name)
		return False

	def add_route (self, rule, routepair, config = None, name = None):
		reverse_proxing = False
		vhost = self.get_vhost (rule)

		if type (routepair) is tuple:
			route, module, path = routepair
			return self.add_app (rule, route, module, path, config)
		route, target = [x.strip () for x in routepair.split ("=", 1)]

		if target.startswith ("@"):
			if route [-1] == "/":
				route = route [:-1]
			vhost.add_proxypass (route, target [1:].strip ())
			reverse_proxing = True

		elif os.path.isdir (target):
			if route [-1] == "/":
				route = route [:-1]
			vhost.add_route (route, target)

		else:
			fullpath = os.path.split (target.strip())
			vhost.add_module (route, os.sep.join (fullpath[:-1]), fullpath [-1], config, name)

		return reverse_proxing

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
