# Web Socket message dump and load related codes are based on websocket-server 0.4
# by Johan Hanssen Seferidis
# https://pypi.python.org/pypi/websocket-server
#
# 2016. 1. 16 Modified by Hans Roh

from . import wsgi_handler
from hashlib import sha1
from base64 import b64encode
from skitai.server.http_response import catch
from aquests.protocols.http import http_util
from skitai import version_info, was as the_was
import threading		
from .websocket import specs
from .websocket import servers
import time
import skitai
import inspect
from skitai.saddle import part

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
		protocol = request.get_header ("http_sec_websocket_protocol", 'unknown')
		securekey = request.get_header ("sec-webSocket-key")
		
		if not origin or not host or not securekey: 
			return request.response.error (400)
		
		if not (host.startswith ("localhost:") or origin.find (host) != -1 or origin == "null"):
			return request.response.error (403)
		
		path, params, query, fragment = request.split_uri ()		
		has_route = self.apps.has_route (path)
		if type (has_route) is int:
			return request.response.error (404)
		
		apph = self.apps.get_app (path)
		if not self.isauthorized (apph.get_callable(), request):
			return
			
		env = self.build_environ (request, apph)
		was = the_was._get ()
		was.request = request
		env ["skitai.was"] = was
		env ["websocket_init"] = ""
		
		is_saddle = isinstance (apph.get_callable (), part.Part)
		message_encoding = skitai.WS_MSG_DEFAULT	
			
		if not is_saddle:	# not Skitao-Saddle				
			apph (env, donot_response)
			wsconfig = env ["websocket_init"]
			if len (wsconfig) == 3:
				design_spec, keep_alive, varnames = wsconfig				
				if type (varnames) not in (list, tuple):
					varnames = (varnames,)
			else:
				raise AssertionError ("You should return (design_spec, keep_alive, var_names) where env has key 'skitai.websocket_init'")
				
		else:	
			current_app, method, kargs, resp_code = apph.get_callable().get_method (env ["PATH_INFO"])
			if resp_code:
				return request.response.error (resp_code)
			
			wsfunc = method [1]
			fspec = inspect.getargspec (wsfunc)
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
			wsconfig = env ["websocket_init"]
			if not savedqs:
				del env ["QUERY_STRING"]
			else:	
				env ["QUERY_STRING"] = savedqs
			
			keep_alive = 60
			try:	
				if len (wsconfig) == 3:
					design_spec, keep_alive, message_encoding = wsconfig					
				elif len (wsconfig) == 2:
					design_spec, keep_alive = wsconfig
				elif len (wsconfig) == 1:
					design_spec = wsconfig [0]				
			except:
				self.wasc.logger.trace ("server",  request.uri)
				return request.response.error (500, why = apph.debug and catch (1) or "")			
		
		del env ["websocket_init"]
		assert design_spec in (1,2,4,5), "design_spec  should be one of (WS_SIMPLE, WS_GROUPCHAT, WS_DEDICATE, WS_DEDICATE_TS)"			
		headers = [
			("Sec-WebSocket-Accept", self.calculate_response_key (securekey)),
			("Upgrade", "Websocket"),
			("Connection", "Upgrade"),
      ("WebSocket-Protocol", protocol),
      ("WebSocket-Location", "ws://" + host + path)
		]
		request.response ("101 Web Socket Protocol Handshake", headers = headers)		
		
		if design_spec == skitai.WS_SIMPLE:
			varnames = varnames [:1]
			# WEBSOCKET_REQDATA			
			# Like AJAX, simple request of client, simple response data
			# the simplest version of stateless HTTP protocol using basic skitai thread pool
			ws = specs.WebSocket1 (self, request, apph, env, varnames, message_encoding)
			env ["websocket"] = ws
			if is_saddle: env ["websocket.handler"] = (current_app, wsfunc)		
			
		elif design_spec == skitai.WS_GROUPCHAT:
			# WEBSOCKET_GROUPCHAT
			# /chat?roomid=456, 
			# return (WEBSOCKET_GROUPCHAT, 600)
			# non-threaded websocketserver
			# can send to all clients of group / specific client
			varnames = varnames [:4]
			param_name = varnames [2]
			gid = http_util.crack_query (query).get (param_name, None)
			try:
				assert gid, "%s value can't find" % param_name
			except:
				self.wasc.logger.trace ("server",  request.uri)
				return request.response.error (500, why = apph.debug and catch (1) or "")
			gid = "%s/%s" % (path, gid)
			
			if not servers.websocket_servers.has_key (gid):
				server = servers.websocket_servers.create (gid, self, request, apph, env, message_encoding)				
				env ["websocket"] = server
				if is_saddle: env ["websocket.handler"] = (current_app, wsfunc)
			
			server = servers.websocket_servers.get (gid)							
			ws = specs.WebSocket5 (self, request, server, env, varnames)
			server.add_client (ws)
			
		else: # 2, 4
			# WEBSOCKET_DEDICATE 			
			# 1:1 wesocket:thread
			# Be careful, it will be consume massive thread resources			
			if design_spec == skitai.WS_DEDICATE:
				ws = specs.WebSocket2 (self, request, message_encoding)
			else:
				ws = specs.WebSocket4 (self, request, message_encoding)
			request.channel.use_sendlock ()
			env ["websocket"] = ws
			job = specs.DedicatedJob (request, apph, (env, donot_response), self.wasc.logger)
			threading.Thread (target = job).start ()
		
		request.channel.die_with (ws, "websocket spec. %d" % design_spec)
		self.channel_config (request, ws, keep_alive)
		
	def channel_config (self, request, ws, keep_alive):
		request.response.done (upgrade_to =  (ws, 2))		
		request.channel.set_timeout (keep_alive)
	
	