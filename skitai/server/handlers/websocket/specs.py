import sys
import struct
from .. import wsgi_handler
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

class WebSocket4 (WebSocket2):
	# WEBSOCKET_DEDICATE_THREADSAFE
	def __init__ (self, handler, request):
		WebSocket2.__init__ (self, handler, request)
		self.lock = threading.Lock ()
		
	def send (self, message, op_code = OPCODE_TEXT):
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
