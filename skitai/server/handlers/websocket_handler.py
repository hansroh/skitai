# Web Socket message dump and load related codes are based on websocket-server 0.4
# by Johan Hanssen Seferidis
# https://pypi.python.org/pypi/websocket-server
#
# 2016. 1. 16 Modified by Hans Roh

import sys
import struct
from . import wsgi_handler
from hashlib import sha1
from base64 import b64encode
import time
from skitai.server.http_response import catch
from skitai.server.threads import trigger
try:
	from urllib.parse import quote_plus
except ImportError:
	from urllib import quote_plus	
from skitai.lib import strutil
from skitai import version_info, was as the_was
try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO
import threading
import zlib
import threading

FIN    = 0x80
OPCODE = 0x0f
MASKED = 0x80
PAYLOAD_LEN = 0x7f
PAYLOAD_LEN_EXT16 = 0x7e
PAYLOAD_LEN_EXT64 = 0x7f

OPCODE_TEXT = 0x01
OPCODE_BINARY = 0x02
CLOSE_CONN  = 0x8


class WebSocket:
	collector = None
	producer = None
	
	def __init__ (self, handler, request):		
		self.handler = handler		
		self.wasc = handler.wasc
		self.request = request		
		self.channel = request.channel
		self.channel.set_terminator (None)
		self.rfile = BytesIO ()
		self.masks = b""
		self.opcode = None
		self._closed = False
		
	def close (self):		
		if self._closed: return
		self._closed = True
		self.channel.current_request = None  # break circ. ref
		self.handler.finish_request (self.request)		
	
	def closed (self):
		return self._closed
				
	def _tobytes (self, b):
		if sys.version_info[0] < 3:
			return map(ord, bytes)
		else:
			return b
		
	def collect_incoming_data (self, data):
		if not data:
			# closed connection
			self.close ()
			return
		
		if self.masks:
			self.rfile.write (data)
			return
			
		b1, b2 = self._tobytes(data [:2])		
		
		fin    = b1 & FIN
		opcode = b1 & OPCODE
		if opcode == CLOSE_CONN:
			self.close ()
			return
		mask = b2 & MASKED
		if not mask:
			raise AssertionError ("Client should always mask")			
		payload_length = b2 & PAYLOAD_LEN
		if payload_length == 0:
			self.found_terminator ()
			return
		
		if payload_length < 126:
			masks = data [2:6]
			payload_start = 6
			
		elif payload_length == 126:
			payload_length = struct.unpack(">H", self._tobytes(data [2:4]))[0]
			masks = data [4:8]
			payload_start = 8
			
		elif payload_length == 127:
			payload_length = struct.unpack(">Q", self._tobytes(data [2:10]))[0]
			masks = data [10:14]		
			payload_start = 14	
		
		self.rfile.write (data [payload_start:])
		self.opcode = opcode
		self.masks = masks
			
		want = payload_length - (len (data) - payload_start)
		if not want:
			self.found_terminator ()
			return
		self.channel.set_terminator (want)
		
	def found_terminator (self):
		self.channel.set_terminator (None)
		masked_data = bytearray(self.rfile.getvalue ())
		masking_key = bytearray(self.masks)
		data = bytearray ([masked_data[i] ^ masking_key [i%4] for i in range (len (masked_data))])
		
		if self.opcode == OPCODE_TEXT:
			# text
			data = data.decode('utf-8')
		
		self.opcode = None
		self.masks = b""
		self.rfile.seek (0)
		self.rfile.truncate ()
		self.handle_message (data)
		
	def send (self, message, op_code = OPCODE_TEXT):
		header  = bytearray()
		if strutil.is_encodable (message):
			payload = message.encode ("utf8")
		else:
			payload = message
		payload_length = len(payload)

		# Normal payload
		if payload_length <= 125:
			header.append(FIN | op_code)
			header.append(payload_length)

		# Extended payload
		elif payload_length >= 126 and payload_length <= 65535:
			header.append(FIN | op_code)
			header.append(PAYLOAD_LEN_EXT16)
			header.extend(struct.pack(">H", payload_length))

		# Huge extended payload
		elif payload_length < 18446744073709551616:
			header.append(FIN | op_code)
			header.append(PAYLOAD_LEN_EXT64)
			header.extend(struct.pack(">Q", payload_length))
						
		else:
			raise AssertionError ("Message is too big. Consider breaking it into chunks.")
		
		m = header + payload
		trigger.wakeup (lambda p=self.channel, d=m: (p.push (d),))
	
	def handle_message (self, msg):
		raise NotImplementedError ("handle_message () not implemented")
		
	
class WebSocket1 (WebSocket):
	# WEBSOCKET_REQDATA			
	def __init__ (self, handler, request, apph, env):
		WebSocket.__init__ (self, handler, request)
		self.apph = apph
		self.env = env
		self.querystring = self.env.get ("QUERY_STRING", "")
		if self.querystring:
			self.querystring += "&"
		self.querystring += "message="
		
	def handle_message (self, msg):
		self.env ["QUERY_STRING"] = self.querystring + quote_plus (msg)		
		if self.env ["wsgi.multithread"]:
			args = (self.request, self.apph, (self.env, self.send), self.wasc.logger)
			self.wasc.queue.put (Job1 (*args))
		else:
			Job1 (*args) ()

class Job1 (wsgi_handler.Job):
	def exec_app (self):
		was = the_was._get ()
		was.request = self.request
		self.args [0]["skitai.was"] = was
		try:
			content = self.apph (*self.args)
		except:
			content = self.apph.debug and "[ERROR]" + catch (0) or "[ERROR]"
		self.args [1] (content [0])


class WebSocket2 (WebSocket):
	# WEBSOCKET_DEDICATE if lock is None, or WEBSOCKET_MULTICAST
	def __init__ (self, handler, request):
		WebSocket.__init__ (self, handler, request)
		self.cv = threading.Condition (threading.RLock ())
		self.messages = []
	
	def wait (self, timeout = 10):
		self.cv.acquire()
		while not self.messages:
			self.cv.wait(timeout)
			if self.messages or self.closed ():
				break
		self.cv.release()		
		
	def handle_message (self, msg):
		self.cv.acquire()
		self.messages.append (msg)
		self.cv.notify ()
		self.cv.release ()


class WebSocket3 (WebSocket):
	# WEBSOCKET_MULTICAST
	def __init__ (self, handler, request, server):
		WebSocket.__init__ (self, handler, request)
		self.client_id = ws.channel.channel_number
		self.server = server
	
	def handle_message (self, msg):
		self.server.push (self.client_id, msg)


class WebSocketServer (WebSocket2):
	# WEBSOCKET_DEDICATE if lock is None, or WEBSOCKET_MULTICAST
	def __init__ (self, handler):
		self.handler = handler
		self.cv = threading.Condition (threading.RLock ())
		self.messages = []
		self.clients = {}
	
	def add_client (self, ws):
		self.clients [ws.client_id] = ws
	
	def push (self, client_id, msg):
		self.cv.acquire()
		self.messages.append ((client_id, msg))
		self.cv.notify ()
		self.cv.release ()
			
	def wait (self, timeout = 10):
		self.cv.acquire()
		while not self.messages:
			self.cv.wait(timeout)
			if self.messages or self.closed ():
				break
		self.cv.release()		
	
	def send (self, client_id, msg):
		self.clients [client_id].send (msg)
	
	def send_all (self, msg, exclude_client_id = None):
		for client_id in self.clients:
			if client_id != exclude_client_id:
		 		self.send (client_id, msg)
		
	
class Job23 (Job1):
	def exec_app (self):
		was = the_was._get () # create new was, cause of non thread pool
		was.request = self.request
		self.args [0]["skitai.was"] = was
		try:
			self.apph (*self.args)
		except:
			self.logger.trace ("app")
		the_was._del () # remove

	

class Handler (wsgi_handler.Handler):
	def __init__ (self, wasc, apps):
		wsgi_handler.Handler.__init__ (self, wasc, apps)		
		self.websocket_servers = {} # For WEBSOCKET_MULTICAST
			
	def match (self, request):
		connection = request.get_header ("connection")
		return connection and connection.lower ().find ("upgrade") != -1 and request.version == "1.1" and request.command == "get"
	
	GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'.encode ()
	def calculate_response_key (self, key):		
		hash = sha1(key.encode() + self.GUID)
		response_key = b64encode(hash.digest()).strip()
		return response_key.decode('ASCII')
		
	def handle_request (self, request):
		
		def donot_response (self, *args, **kargs):
			raise AssertionError ("Websocket can't use start_response ()")
		
		origin = request.get_header ("origin")
		host = request.get_header ("host")
		protocol = request.get_header ("http_sec_websocket_protocol", 'unknown')
		securekey = request.get_header ("sec-webSocket-key")
		
		if not origin or not host or not securekey: 
			return request.response.error (400)		
		
		path, params, query, fragment = request.split_uri ()		
		has_route = self.apps.has_route (path)
		if type (has_route) is int:
			return request.response.error (404)
		if not self.authorized (request, has_route):
			return
		
		apph = self.apps.get_app (path)
		env = self.build_environ (request, apph)
		was = the_was._get ()
		was.request = request
		env ["skitai.was"] = was
		env ["skitai.websocket_init"] = ""
		# app should reply  (design type one of (1,2,3), keep-alive seconds)
		# when env has 'skitai.websocket_init'
		try:
			ws_design = apph (env, donot_response)
		except:
			self.wasc.logger.trace ("server",  request.uri)
			return request.response.error (500, why = apph.debug and catch (1) or "")	
		
		try: 
			ws_design, keep_alive = ws_design [0]
		except (IndexError, ValueError): ws_design = (-1, 0)
		
		if ws_design not in (1,2,3):			
			return request.response.error (503)
		
		header = [
			("Sec-WebSocket-Accept", self.calculate_response_key (securekey)),
			("Upgrade", "Websocket"),
			("Connection", "Upgrade"),
			# TODO ("WebSocket-Origin", origin),
      ("WebSocket-Protocol", protocol),
      ("WebSocket-Location", "ws://" + host + path)
		]
		request.response.start_response ("101 Web Socket Protocol Handshake", header)
		request.response.done ()
		
		del env ["skitai.websocket_init"]
		request.channel.keep_alive = keep_alive
		request.channel.response_timeout = keep_alive
		
		if ws_design == 1: # WEBSOCKET_REQDATA			
			ws = WebSocket1 (self, request, apph, env)			
		
		elif ws_design == 2: #WEBSOCKET_DEDICATE 
			ws = WebSocket2 (self, request)
			env ["websocket"] = ws
			request.channel.current_request = ws
			args = (request, apph, (env, donot_response), self.wasc.logger)
			threading.Thread (target = Job2, args = args).start ()
		
		else: # WEBSOCKET_MULTICAST
			if path not in self.websocket_servers:
				wss = WebSocketServer ()
				self.websocket_servers [path] = wss
				env ["websocket"] = wss				
				args = (request, apph, (env, donot_response), self.wasc.logger)
				threading.Thread (target = Job2, args = args).start ()				
			ws = WebSocket3 (self, request)
			request.channel.current_request = ws
			self.websocket_servers [path].add_client (ws)
		
	def finish_request (self, request):		
		if request.channel:
			request.channel.close ()
	
