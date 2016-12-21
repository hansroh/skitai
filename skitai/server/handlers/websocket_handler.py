# Web Socket message dump and load related codes are based on websocket-server 0.4
# by Johan Hanssen Seferidis
# https://pypi.python.org/pypi/websocket-server
#
# 2016. 1. 16 Modified by Hans Roh

from . import wsgi_handler
from hashlib import sha1
from base64 import b64encode
from skitai.server.http_response import catch
from skitai.server import utility
from skitai import version_info, was as the_was
import threading		
from .websocket import specs
from .websocket.servers import websocket_servers

class Handler (wsgi_handler.Handler):
	def match (self, request):
		upgrade = request.get_header ("upgrade")
		return upgrade and upgrade.lower ().startswith ("websocket") and request.version == "1.1" and request.command == "get"
	
	def close (self):
		websocket_servers.close ()
	
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
		# app should reply  (design type one of (1,2,3), keep-alive seconds)
		# when env has 'skitai.websocket_init'
		try:
			apph (env, donot_response)
			try:
				design_spec, keep_alive, param_name = env ["websocket_init"]
				del env ["websocket_init"]
			except (IndexError, ValueError): 
				raise AssertionError ("You should return (design_spec, keep_alive, param_name) where env has key 'skitai.websocket_init'")				
			assert design_spec in (1,2,3,4), "design_spec  should be one of (WEBSOCKET_REQDATA, WEBSOCKET_DEDICATE, WEBSOCKET_DEDICATE_THREADSAFE, WEBSOCKET_MULTICAST)"			
		except:
			self.wasc.logger.trace ("server",  request.uri)
			return request.response.error (500, why = apph.debug and catch (1) or "")
		
		headers = [
			("Sec-WebSocket-Accept", self.calculate_response_key (securekey)),
			("Upgrade", "Websocket"),
			("Connection", "Upgrade"),
      ("WebSocket-Protocol", protocol),
      ("WebSocket-Location", "ws://" + host + path)
		]
		request.response ("101 Web Socket Protocol Handshake", headers = headers)
		
		if design_spec == 1: 
			# WEBSOCKET_REQDATA			
			# Like AJAX, simple request of client, simple response data
			# the simplest version of stateless HTTP protocol using basic skitai thread pool
			ws = specs.WebSocket1 (self, request, apph, env, param_name)
			env ["websocket"] = ws		
			self.channel_config (request, ws, keep_alive)
		
		elif design_spec in (2, 4): 
			# WEBSOCKET_DEDICATE 			
			# 1:1 wesocket:thread
			# Be careful, it will be consume massive thread resources
			if design_spec == 2:
				ws = specs.WebSocket2 (self, request)
			else:
				ws = specs.WebSocket4 (self, request)
			request.channel.add_closing_partner (ws)
			env ["websocket"] = ws
			self.channel_config (request, ws, keep_alive)
			job = specs.Job2 (request, apph, (env, donot_response), self.wasc.logger)
			threading.Thread (target = job).start ()
		
		else: 
			# WEBSOCKET_MULTICAST
			# /chat?roomid=456, 
			# return (WEBSOCKET_MULTICAST, 600, "roomid")
			# websocketserver thread will be created by roomid
			# can send to all clients of group / specific client
			if not param_name:
				gidkey = path
			else:	
				gid = utility.crack_query (query).get (param_name, None)
				try:
					assert gid, "%s value can't find" % param_name
				except:
					self.wasc.logger.trace ("server",  request.uri)
					return request.response.error (500, why = apph.debug and catch (1) or "")
				gid = "%s/%s" % (path, gid)
			
			if not websocket_servers.has_key (gid):
				server = websocket_servers.create (gid)
				request.channel.add_closing_partner (server)
				env ["websocket"] = server
				job = specs.Job3 (server, request, apph, (env, donot_response), self.wasc.logger)
				threading.Thread (target = job).start ()	
			
			server = websocket_servers.get (gid)				
			ws = specs.WebSocket3 (self, request, server)
			server.add_client (ws)
			self.channel_config (request, ws, keep_alive)			
		
	def finish_request (self, request):		
		if request.channel:
			request.channel.close_when_done ()
		
	def channel_config (self, request, ws, keep_alive):
		request.response.done (False, False, False, (ws, 2))
		request.channel.set_response_timeout (keep_alive)
		request.channel.set_keep_alive (keep_alive)
		