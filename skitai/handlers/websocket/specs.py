import sys
import struct
import threading
import json
import skitai
from .. import wsgi_handler
from skitai.http_response import catch
from aquests.athreads import trigger
from rs4 import strutil
from aquests.protocols.grpc import discover
from aquests.protocols.ws import *
from aquests.protocols.http import http_util
from skitai import version_info, was as the_was
try: import xmlrpc.client as xmlrpclib
except ImportError: import xmlrpclib
try: from urllib.parse import quote_plus
except ImportError: from urllib import quote_plus	
try: from cStringIO import StringIO as BytesIO
except ImportError: from io import BytesIO
import copy
from collections import Iterable
from rs4.reraise import reraise 
from ...http_response import catch

has_werkzeug = True
try:
	from werkzeug.wsgi import ClosingIterator 
except ImportError:
	has_werkzeug = False	

class WebSocket:
	collector = None
	producer = None
	
	def __init__ (self, handler, request, message_encoding = None):		
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
		self.default_op_code = OPCODE_TEXT
		self._closed = False
		self.encoder_config = None	
		self.message_encoding = self.setup_encoding (message_encoding)
		
	def close (self):
		if self._closed: return
		self._closed = True		
	
	def closed (self):
		return self._closed
	
	def setup_encoding (self, message_encoding):	
		if message_encoding == skitai.WS_MSG_GRPC:
			i, o = discover.find_type (request.uri [1:])
			self.encoder_config = (i [0], 0 [0])
			self.default_op_code = OP_BINARY
			self.message_encode = self.grpc_encode
			self.message_decode = self.grpc_decode			
		elif message_encoding == skitai.WS_MSG_JSON:
			self.message_encode = json.dumps
			self.message_decode = json.loads
		elif message_encoding == skitai.WS_MSG_XMLRPC:
			self.message_encode = xmlrpclib.dumps
			self.message_decode = xmlrpclib.loads
		else:
			self.message_encode = self.transport
			self.message_decode = self.transport
		return message_encoding
	
	def transport (self, msg):
		return msg
		
	def grpc_encode (self, msg):
		f = self.encoder_config [0] ()
		f.ParseFromString (msg)
		return f
	
	def grpc_decode (self, msg):
		return msg.SerializeToString ()
						
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
			self.buf += data
	
	def found_terminator (self):
		buf, self.buf = self.buf, b""
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
			if self.opcode == OPCODE_PING:
				self.send (data, OPCODE_PONG)
			else:	
				self.handle_message (data)
		
		elif self.payload_length:
			self.masks = buf
			self.channel.set_terminator (self.payload_length)
		
		elif self.opcode:			
			if len (buf) == 2:
				fmt = ">H"
			else:	
				fmt = ">Q"
			self.payload_length = struct.unpack(fmt, self._tobytes(buf))[0]
			if self.has_masks:
				self.channel.set_terminator (4) # mask
			else:
				self.channel.set_terminator (self.payload_length)
		
		elif self.opcode is None:
			b1, b2 = self._tobytes(buf)
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
	
	def build_data (self, message, op_code):
		if has_werkzeug and isinstance (message, ClosingIterator):
			msgs = []
			for msg in message:
				msgs.append (msg)
			message = b''.join (msgs).decode ("utf8")
		else:
			message = self.message_encode (message)
		
		if op_code == -1:
			if type (message) is str:
				op_code = OPCODE_TEXT
			elif type (message) is bytes:	
				op_code = OPCODE_BINARY
			if op_code == -1:
				op_code = self.default_op_code
		return message, op_code
							
	def send (self, message, op_code = -1):
		if not self.channel: return
		message, op_code = self.build_data (message, op_code)		
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
		self._send (m)
	
	def _send (self, msg):	
		if self.channel:
			if hasattr (self.wasc, 'threads'):
				trigger.wakeup (lambda p=self.channel, d=msg: (p.push (d),))
			else:
				self.channel.push (msg)
	
	def handle_message (self, msg):
		raise NotImplementedError ("handle_message () not implemented")

#---------------------------------------------------------

class Job (wsgi_handler.Job):	
	def exec_app (self):
		was = the_was._get ()
		was.request = self.request
		was.env = self.args [0]
		
		was.websocket = self.args [0]["websocket"]
		self.args [0]["skitai.was"] = was
		content = self.apph (*self.args)
		if content:
			if type (content) is not tuple:
				content = (content,)
			was.websocket.send (*content)
		
		was.request = None
		was.env = None
		was.websocket = None

#---------------------------------------------------------
	
class WebSocket1 (WebSocket):
	# WEBSOCKET_REQDATA			
	def __init__ (self, handler, request, apph, env, param_names, message_encoding = None):
		WebSocket.__init__ (self, handler, request, message_encoding)
		self.client_id = request.channel.channel_number		
		self.apph = apph
		self.env = env
		self.param_names = param_names
		self.set_query_string ()
		
	def start_response (self, message, headers = None, exc_info = None):		
		if exc_info:
			reraise (*exc_info)		
	
	def set_query_string (self):
		querystring = []		
		if self.env.get ("QUERY_STRING"):
			querystring.append (self.env.get ("QUERY_STRING"))		
		querystring.append ("%s=" % self.param_names [0])
		self.querystring = "&".join (querystring)		
		self.params = http_util.crack_query (self.querystring)		
	
	def open (self):		
		self.handle_message (-1, skitai.WS_EVT_OPEN)
		if "websocket.handler" in self.env:
			app = self.apph.get_callable ()
			app.register_websocket (self.client_id, self.send)

	def close (self):
		if "websocket.handler" in self.env:
			app = self.apph.get_callable ()
			app.remove_websocket (self.client_id)			
		if not self.closed ():			
			self.handle_message (-1, skitai.WS_EVT_CLOSE)
			WebSocket.close (self)
		
	def make_params (self, msg, event):
		querystring = self.querystring
		params = self.params
		if event:
			self.env ['websocket.event'] = event
		else:	
			self.env ['websocket.event'] = None
			querystring = querystring + quote_plus (msg)
			params [self.param_names [0]] = self.message_decode (msg)
		return querystring, params
	
	def handle_message (self, msg, event = None):		
		if not msg: return			
		querystring, params = self.make_params (msg, event)
		self.env ["QUERY_STRING"] = querystring
		self.env ["websocket.params"] = params
		self.env ["websocket.client"] = self.client_id		
		self.execute ()
	
	def execute (self):
		args = (self.request, self.apph, (self.env, self.start_response), None, self.wasc.logger)
		if not self.env ["wsgi.multithread"]:
			Job (*args) ()			
		else:
			self.wasc.queue.put (Job (*args))


class WebSocket6 (WebSocket1):
	# WEBSOCKET_REQDATA			
	def __init__ (self, handler, request, apph, env, param_names, message_encoding = None):
		WebSocket1.__init__ (self, handler, request, apph, env, param_names, message_encoding)
		self.lock = threading.Lock ()
	
	def _send (self, msg):
		with self.lock:
			WebSocket1._send (self, msg)

					
class WebSocket5 (WebSocket1):
	# WEBSOCKET_MULTICAST
	def __init__ (self, handler, request, server, env, param_names):
		WebSocket.__init__ (self, handler, request)
		self.server = server
		self.apph = server.apph
		self.client_id = request.channel.channel_number		
		self.env = env
		self.param_names = param_names
		self.set_query_string ()
	
	def set_query_string (self):
		WebSocket1.set_query_string (self)
		
	def handle_message (self, msg, event = None):
		if not msg: return			
		querystring, params = self.make_params (msg, event)			

		self.server.handle_message (
			self.client_id, 
			msg, 
			querystring,
			params, 
			self.param_names [0]
		)

