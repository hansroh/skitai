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
from skitai.server import utility
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

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xa


class WebSocket:
	collector = None
	producer = None
	
	def __init__ (self, handler, request):		
		self.handler = handler		
		self.wasc = handler.wasc
		self.request = request		
		self.channel = request.channel
		self.channel.set_terminator (2)
		self.rfile = BytesIO ()
		self.masks = b""
		self.has_masks = True
		self.buf = b""
		self.payload_length = 0
		self.opcode = None
		self._closed = False
		
	def close (self):
		if self._closed: return
		self._closed = True
		if self.channel:
			self.channel.current_request = None  # break circ. ref
		self.handler.finish_request (self.request)		
	
	def closed (self):
		return self._closed
				
	def _tobytes (self, b):
		if sys.version_info[0] < 3:
			return map(ord, b)
		else:
			return b
		
	def collect_incoming_data (self, data):
		#print (">>>>", data)
		if not data:
			# closed connection
			self.close ()
			return
		
		if self.masks or (not self.has_masks and self.payload_length):
			self.rfile.write (data)			
		else:
			self.buf = data
	
	def found_terminator (self):
		#print ("-----", self.buf, self.opcode, self.payload_length, self.masks)
		if self.masks or (not self.has_masks and self.payload_length):
			# end of message
			masked_data = bytearray(self.rfile.getvalue ())
			if self.masks:
				masking_key = bytearray(self.masks)
				data = bytearray ([masked_data[i] ^ masking_key [i%4] for i in range (len (masked_data))])
			else:
				data = masked_data	
			
			if self.opcode == OPCODE_TEXT:
				# text
				data = data.decode('utf-8')
		
			self.payload_length = 0
			self.opcode = None
			self.masks = b""
			self.has_masks = True
			self.rfile.seek (0)
			self.rfile.truncate ()
			self.channel.set_terminator (2)
			self.handle_message (data)
		
		elif self.payload_length:
			self.masks = self.buf
			self.channel.set_terminator (self.payload_length)
		
		elif self.opcode:			
			if len (self.buf) == 2:
				fmt = ">H"
			else:	
				fmt = ">Q"
			self.payload_length = struct.unpack(fmt, self._tobytes(self.buf))[0]
			if self.has_masks:
				self.channel.set_terminator (4) # mask
			else:
				self.channel.set_terminator (self.payload_length)
		
		elif self.opcode is None:
			b1, b2 = self._tobytes(self.buf)
			fin    = b1 & FIN
			self.opcode = b1 & OPCODE
			#print (fin, self.opcode)
			if self.opcode == OPCODE_CLOSE:
				self.close ()
				return
				
			mask = b2 & MASKED
			if not mask:
				self.has_masks = False
			
			payload_length = b2 & PAYLOAD_LEN
			if payload_length == 0:
				self.opcode = None
				self.has_masks = True
				self.channel.set_terminator (2)
				return
			
			if payload_length < 126:
				self.payload_length = payload_length
				if self.has_masks:
					self.channel.set_terminator (4) # mask
				else:
					self.channel.set_terminator (self.payload_length)
			elif payload_length == 126:
				self.channel.set_terminator (2)	# short length
			elif payload_length == 127:
				self.channel.set_terminator (8) # long length
		
		else:
			raise AssertionError ("Web socket frame decode error")
			
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
	def __init__ (self, handler, request, apph, env, param_name):
		WebSocket.__init__ (self, handler, request)
		self.apph = apph
		self.env = env
		self.querystring = self.env.get ("QUERY_STRING", "")
		if self.querystring:
			self.querystring += "&"
		self.querystring += "%s=" % param_name
		
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
			content = self.apph (*self.args) [0]
		except:
			content = self.apph.debug and "[ERROR]" + catch (0) or "[ERROR]"
		self.args [1] (content)


class WebSocket2 (WebSocket):
	# WEBSOCKET_DEDICATE if lock is None, or WEBSOCKET_MULTICAST
	def __init__ (self, handler, request):
		WebSocket.__init__ (self, handler, request)
		self.cv = threading.Condition (threading.RLock ())
		self.messages = []		
	
	def close (self):
		WebSocket.close (self)
		self.cv.acquire()
		self.cv.notify ()
		self.cv.release ()
		
	def getswait (self, timeout = 10):
		if self._closed:
			return None # closed channel
		self.cv.acquire()
		while not self.messages and not self._closed:
			self.cv.wait(timeout)
		if self._closed:
			self.cv.release()
			return None
		messages = self.messages
		self.messages = []
		self.cv.release()
		return messages
	
	def handle_message (self, msg):		
		self.cv.acquire()
		self.messages.append (msg)
		self.cv.notify ()
		self.cv.release ()

class Job2 (Job1):
	def handle_error (self):
		pass
		
	def exec_app (self):
		was = the_was._get () # create new was, cause of non thread pool
		was.request = self.request
		self.args [0]["skitai.was"] = was
		try:
			self.apph (*self.args)
		except:
			self.handle_error ()
			self.logger.trace ("app")
		the_was._del () # remove


class WebSocket3 (WebSocket):
	# WEBSOCKET_MULTICAST
	def __init__ (self, handler, request, server):
		WebSocket.__init__ (self, handler, request)
		self.client_id = request.channel.channel_number
		self.server = server
	
	def handle_message (self, msg):
		self.server.handle_message (self.client_id, msg)
	
	def close (self):
		WebSocket.close (self)
		self.server.handle_close (self.client_id)


class Job3 (Job2):
	def __init__(self, server, request, apph, args, logger):
		self.server = server
		Job2.__init__(self, request, apph, args, logger)
		
	def handle_error (self):
		self.server.close ()
		

class WebSocketServers:
	def __init__ (self):
		self.lock = threading.RLock ()
		self.wss = {}
	
	def get (self, gid):
		self.lock.acquire ()
		wss = self.wss [gid]
		self.lock.release ()
		return wss
		
	def has_key (self, gid):	
		self.lock.acquire ()
		has = gid in self.wss
		self.lock.release ()
		return has
		
	def create (self, gid):	
		self.lock.acquire ()
		wss = WebSocketServer (gid)
		self.wss [gid] = wss
		self.lock.release ()
		return wss
	
	def remove (self, gid):
		self.lock.acquire ()
		try: 
			del self.wss [gid]			
		except KeyError: 
			pass	
		self.lock.release ()		
	
	def close (self):
		self.lock.acquire ()
		for s in list (self.wss.values ()):
			s.close ()
		self.lock.release ()

websocket_servers = WebSocketServers ()
			
class WebSocketServer (WebSocket2):
	def __init__ (self, gid):
		self._closed = False
		self.gid = gid
		self.lock = threading.RLock ()
		self.cv = threading.Condition ()
		self.messages = []
		self.clients = {}
		
	def add_client (self, ws):
		self.lock.acquire ()
		self.clients [ws.client_id] = ws
		self.lock.release ()
		self.handle_message (ws.client_id, 1)
	
	def handle_close (self, client_id):
		self.lock.acquire ()
		try: del self.clients [client_id]
		except KeyError: pass		
		self.lock.release ()
		self.handle_message (client_id, -1)
		
	def handle_message (self, client_id, msg):
		self.cv.acquire()
		self.messages.append ((client_id, msg))
		self.cv.notifyAll ()
		self.cv.release ()
			
	def close (self):
		websocket_servers.remove (self.gid)
		self.clients = {}
		self.cv.acquire()
		self._closed = True
		self.cv.notifyAll ()
		self.cv.release ()
		
	def send (self, *args, **karg):
		raise AssertionError ("Can't use send() on WEBSOCKET_MULTICAST spec, use send_to(client_id, msg, op_code)")
	
	def sendto (self, client_id, msg, op_code = OPCODE_TEXT):		
		self.lock.acquire ()
		try:
			client = self.clients [client_id]
		except KeyError:
			client = None	
		self.lock.release ()
		if client:
			client.send (msg, op_code)
		
	def sendall (self, msg, op_code = OPCODE_TEXT):
		self.lock.acquire ()
		clients = list (self.clients.keys ())
		self.lock.release ()
		for client_id in clients:
			self.sendto (client_id, msg)
	

class Handler (wsgi_handler.Handler):
	def match (self, request):
		connection = request.get_header ("connection")
		return connection and connection.lower ().find ("upgrade") != -1 and request.version == "1.1" and request.command == "get"
	
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
		if not self.authorized (apph.get_callable(), request, has_route):
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
			assert design_spec in (1,2,3), "design_spec  should be one of (WEBSOCKET_REQDATA, WEBSOCKET_DEDICATE, WEBSOCKET_MULTICAST)"			
		except:
			self.wasc.logger.trace ("server",  request.uri)
			return request.response.error (500, why = apph.debug and catch (1) or "")
		
		header = [
			("Sec-WebSocket-Accept", self.calculate_response_key (securekey)),
			("Upgrade", "Websocket"),
			("Connection", "Upgrade"),
      ("WebSocket-Protocol", protocol),
      ("WebSocket-Location", "ws://" + host + path)
		]
		request.response.start_response ("101 Web Socket Protocol Handshake", header)
		request.response.done ()
		
		if design_spec == 1: 
			# WEBSOCKET_REQDATA			
			# Like AJAX, simple request of client, simple response data
			# the simplest version of stateless HTTP protocol using basic skitai thread pool
			ws = WebSocket1 (self, request, apph, env, param_name)
			env ["websocket"] = ws		
			self.channel_config (request, ws, keep_alive)
		
		elif design_spec == 2: 
			# WEBSOCKET_DEDICATE 			
			# 1:1 wesocket:thread
			# Be careful, it will be consume massive thread resources
			ws = WebSocket2 (self, request)
			request.channel.add_closing_partner (ws)
			env ["websocket"] = ws
			self.channel_config (request, ws, keep_alive)
			job = Job2 (request, apph, (env, donot_response), self.wasc.logger)
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
				job = Job3 (server, request, apph, (env, donot_response), self.wasc.logger)
				threading.Thread (target = job).start ()	
			
			server = websocket_servers.get (gid)				
			ws = WebSocket3 (self, request, server)
			server.add_client (ws)
			self.channel_config (request, ws, keep_alive)			
		
	def finish_request (self, request):		
		if request.channel:
			request.channel.close_when_done ()
		
	def channel_config (self, request, ws, keep_alive):
		request.channel.current_request = ws
		request.channel.set_response_timeout (keep_alive)
		