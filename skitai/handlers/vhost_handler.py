import skitai
from ..wastuff import wsgi_apps
import os

class VHost:
	def __init__ (self, wasc, static_max_ages):
		from . import default_handler, wsgi_handler, websocket_handler
		from . import http2_handler

		self.wasc = wasc

		self.apps = wsgi_apps.ModuleManager(self.wasc, self)
		self.handlers = []

		self.access_handler = None
		alternative_handlers = []
		alternative_handlers.append (websocket_handler.Handler (self.wasc, self.apps))
		self.wsgi_handler = wsgi_handler.Handler (self.wasc, self.apps)
		alternative_handlers.append (self.wsgi_handler)
		self.default_handler = default_handler.Handler (self.wasc, {}, static_max_ages, alternative_handlers)
		self.wsgi_handler.set_static_file_translator (self.default_handler.get_static_file_translator ())

		if self.wasc.httpserver.altsvc:
			from . import http3_handler
			self.handlers.append (http3_handler.Handler (self.wasc, self.default_handler))
		self.handlers.append (http2_handler.Handler (self.wasc, self.default_handler))

	def close (self):
		for h in self.handlers:
			try: h.close ()
			except AttributeError: pass
		self.apps.cleanup ()

	def add_route (self, route, target, config):
		self.default_handler.add_route (route, target, config)

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

	def add_route (self, rule, routepair, config = None, name = None):
		vhost = self.get_vhost (rule)

		if type (routepair) is tuple:
			route, module, path = routepair
			if isinstance (module, tuple):
				module, path = module
			self.add_app (rule, route, module, path, config, name)
			return 'A'

		route, target = [x.strip () for x in routepair.split ("=", 1)]
		if os.path.isdir (target):
			if route [-1] == "/":
				route = route [:-1]
			vhost.add_route (route, target, config)
			return 'D'

		fullpath = os.path.split (target.strip())
		vhost.add_module (route, os.sep.join (fullpath[:-1]), fullpath [-1], config, name)
		return 'A'

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
