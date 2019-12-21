# Web Socket message dump and load related codes are based on websocket-server 0.4
# by Johan Hanssen Seferidis
# https://pypi.python.org/pypi/websocket-server
#
# 2016. 1. 16 Modified by Hans Roh

from . import wsgi_handler
from hashlib import sha1
from base64 import b64encode
from ..backbone.http_response import catch
from aquests.protocols.http import http_util
from skitai import version_info, was as the_was
import threading
from .websocket import specs
from .websocket import servers
import time
import skitai
import inspect

class Handler (wsgi_handler.Handler):
	def match (self, request):
		upgrade = request.get_header ("upgrade")
		return upgrade and upgrade.lower ().startswith ("websocket") and request.version == "1.1" and request.command == "get"

	def close (self):
		servers.websocket_servers.close ()

	GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'.encode ()
	def calculate_response_key (self, key):
		hash = sha1(key.encode() + self.GUID)
		response_key = b64encode(hash.digest()).strip()
		return response_key.decode('ASCII')

	def handle_request (self, request):
		def donot_response (self, *args, **kargs):
			def push (thing):
				raise AssertionError ("Websocket can't use start_response ()")
			return push

		origin = request.get_header ("origin")
		host = request.get_header ("host")
		protocol = request.get_header ("sec-websocket-protocol", 'unknown')
		securekey = request.get_header ("sec-websocket-key")

		if not origin or not host or not securekey:
			return request.response.error (400)

		path, params, query, fragment = request.split_uri ()
		has_route = self.apps.has_route (path)
		if type (has_route) is int:
			return request.response.error (404)

		apph = self.apps.get_app (path)
		app = apph.get_callable()
		is_atila = hasattr (app, 'ATILA_THE_HUN')

		if is_atila:
			# safari does not support Authorization
			if request.get_header ("authorization") and not app.is_authorized (request, app.authenticate):
				return request.response.error (401)
			if not app.is_allowed_origin (request, app.access_control_allow_origin):
				return request.response.error (403)

		env = self.build_environ (request, apph)
		was = the_was._get ()
		was.request = request
		was.env = env

		env ["skitai.was"] = was
		env ["websocket.event"] = skitai.WS_EVT_INIT

		message_encoding = skitai.WS_MSG_DEFAULT
		if not is_atila:	# not Skitao-Atila
			apph (env, donot_response)
			wsconfig = env.get ("websocket.config", ())

			if len (wsconfig) == 3:
				design_spec_, keep_alive, varnames = wsconfig
			elif len (wsconfig) == 4:
				design_spec_, keep_alive, varnames, env ["websocket.session"] = wsconfig
			else:
				raise AssertionError ("You should config (design_spec, keep_alive, var_names) where env has key 'skitai.websocket.config'")
			if type (varnames) not in (list, tuple):
				varnames = (varnames,)

		else:
			current_app, method, kargs, options, resp_code = apph.get_callable().get_method (env ["PATH_INFO"], request)
			if resp_code:
				return request.response.error (resp_code)

			request.env = env # IMP
			env ["wsgi.routed"] = wsfunc = current_app.get_routed (method)
			env ["wsgi.route_options"] = options
			fspec = app.get_function_spec (wsfunc, options.get ('mntopt')) or inspect.getfullargspec (wsfunc)

			savedqs = env.get ('QUERY_STRING', '')
			current_args = {}
			defaults = 0
			if savedqs:
				current_args = http_util.crack_query (env ['QUERY_STRING'])
			if fspec.defaults:
				defaults = len (fspec.defaults)
			varnames = fspec.args [1:]
			temporary_args = "&".join ([arg + "=" for arg in varnames [:len (varnames) - defaults] if current_args.get (arg) is None])
			if temporary_args:
				if savedqs:
					env ['QUERY_STRING'] = savedqs + "&" + temporary_args
				else:
					env ['QUERY_STRING'] = temporary_args

			apph (env, donot_response)
			wsconfig = env.get ("websocket.config")
			if not wsconfig:
				raise AssertionError ("You should config (design_spec, keep_alive, [data_encoding]) where env has key 'was.wsconfig ()'")

			if not savedqs and "QUERY_STRING" in env:
				del env ["QUERY_STRING"]
			else:
				env ["QUERY_STRING"] = savedqs

			keep_alive = 60
			if len (wsconfig) == 4:
				design_spec_, keep_alive, message_encoding, env ["websocket.session"] = wsconfig
			elif len (wsconfig) == 3:
				design_spec_, keep_alive, message_encoding = wsconfig
			elif len (wsconfig) == 2:
				design_spec_, keep_alive = wsconfig
			elif len (wsconfig) == 1:
				design_spec_ = wsconfig [0]

		del env ["websocket.event"]
		del env ["websocket.config"]

		assert (design_spec_ & 31) in (skitai.WS_CHANNEL, skitai.WS_GROUPCHAT, skitai.WS_THREADSAFE_DEPRECATED), "design_spec  should be one of (WS_CHANNEL, WS_GROUPCHAT, WS_THREADSAFE)"
		headers = [
			("Sec-WebSocket-Accept", self.calculate_response_key (securekey)),
			("Upgrade", "Websocket"),
			("Connection", "Upgrade"),
		    ("WebSocket-Protocol", protocol),
	    	("WebSocket-Location", "ws://" + host + path)
		]
		request.response ("101 Web Socket Protocol Handshake", headers = headers)

		env ["wsgi.noenv"] = False
		design_spec = design_spec_ & 31
		if design_spec_ & skitai.WS_NOTHREAD == skitai.WS_NOTHREAD:
			env ["wsgi.multithread"] = 0
		elif design_spec_ & skitai.WS_SESSION == skitai.WS_SESSION:
			env ["wsgi.multithread"] = 0

		if design_spec in (skitai.WS_CHANNEL, skitai.WS_THREADSAFE_DEPRECATED):
			varnames = varnames [:1]
			# Like AJAX, simple request of client, simple response data
			# the simplest version of stateless HTTP protocol using basic skitai thread pool
			ws_class = specs.WebSocket1
			if (design_spec_ & skitai.WS_THREADSAFE == skitai.WS_THREADSAFE) or design_spec == skitai.WS_THREADSAFE_DEPRECATED:
				ws_class = specs.WebSocket6
			ws = ws_class (self, request, apph, env, varnames, message_encoding)
			self.channel_config (request, ws, keep_alive)
			env ["websocket"] = ws
			if is_atila:
				env ["websocket.handler"] = (current_app, wsfunc)
			ws.open ()

		elif design_spec == skitai.WS_GROUPCHAT:
			varnames = varnames [:2]
			param_name = varnames [1]
			gid = http_util.crack_query (query).get (param_name, None)
			try:
				assert gid, "%s value can't find" % param_name
			except:
				self.wasc.logger.trace ("server",  request.uri)
				return request.response.error (500, why = apph.debug and sys.exc_info () or None)
			gid = "%s/%s" % (path, gid)

			if not servers.websocket_servers.has_key (gid):
				server = servers.websocket_servers.create (gid, self, request, apph, env, message_encoding)
				if server is None:
					return request.response.error (503)
				env ["websocket"] = server
				if is_atila: env ["websocket.handler"] = (current_app, wsfunc)

			server = servers.websocket_servers.get (gid)
			ws = specs.WebSocket5 (self, request, server, env, varnames)
			self.channel_config (request, ws, keep_alive)
			server.add_client (ws)

		request.channel.die_with (ws, "websocket spec.%d" % design_spec)

	def channel_config (self, request, ws, keep_alive):
		request.response.done (upgrade_to =  (ws, 2))
		request.channel.set_socket_timeout (keep_alive)
