import sys
import struct
import threading
import json
from .. import wsgi_handler
from skitai.server.http_response import catch
from aquests.lib.athreads import trigger
from aquests.lib import strutil
from aquests.protocols.grpc import discover
from aquests.protocols.ws import *
from skitai import version_info, was as the_was
try: import xmlrpc.client as xmlrpclib
except ImportError: import xmlrpclib
try: from urllib.parse import quote_plus
except ImportError: from urllib import quote_plus	
try: from cStringIO import StringIO as BytesIO
except ImportError: from io import BytesIO

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
		self.default_op_code = OPCODE_TEXT
		self._closed = False
		
	def close (self):
		if self._closed: return
		self._closed = True		
	
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
			self.buf += data
	
	def found_terminator (self):
		#print ("-----", self.buf, self.opcode, self.payload_length, self.masks)
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
			
	def send (self, message, op_code = -1):	
		if op_code == -1:
			op_code = self.default_op_code				
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
	def __init__ (self, handler, request, message_encoding = None):
		WebSocket.__init__ (self, handler, request)
		self.cv = threading.Condition (threading.RLock ())
		self.messages = []		
		
		self.encoder_config = None
		self.message_encoding = self.setup_encoding (message_encoding)
	
	def setup_encoding (self, message_encoding):	
		if message_encoding == "grpc":
			i, o = discover.find_type (request.uri [1:])
			self.encoder_config = (i [0], 0 [0])
			self.default_op_code = OP_BINARY
			self.message_encode = self.grpc_encode
			self.message_decode = self.grpc_decode			
		elif message_encoding == "json":
			self.message_encode = json.dumps
			self.message_decode = json.loads
		elif message_encoding == "xmlrpc":
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
	
	def send (self, message, op_code = -1):		
		WebSocket.send (self, self.message_encode (message), op_code)
			
	def handle_message (self, msg):		
		msg = self.message_decode (msg)
		self.cv.acquire()
		self.messages.append (msg)
		self.cv.notify ()
		self.cv.release ()
		
		
class WebSocket4 (WebSocket2):
	# WEBSOCKET_DEDICATE_THREADSAFE
	def __init__ (self, handler, request, message_encoding = None):
		WebSocket2.__init__ (self, handler, request)
		self.lock = threading.Lock ()
		
	def send (self, message, op_code = -1):
		self.lock.acquire ()
		try:
			WebSocket2.send (self, message, op_code)
		finally:
			self.lock.release ()
			
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
