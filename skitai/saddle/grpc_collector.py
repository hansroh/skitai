from skitai.server.handlers.collectors import FormCollector
from skitai.server import counter
from collections import Iterable
from skitai.protocol.grpc.message import decode_message
import threading
import struct

class grpc_collector (FormCollector):
	stream_id = counter.counter ()
	def __init__ (self, handler, request, *args):
		FormCollector.__init__ (self, handler, request, *args)
		self.stream_id.inc ()
		self._compressed = None
		self._msg_length = 0		
		self.buffer = b""		
		self.msgs = []		
	
	def close (self):
		self.handler.continue_request (self.request, self.msgs)
					
	def start_collect (self):	
		self.request.channel.set_terminator (1)
			
	def collect_incoming_data (self, data):
		#print ('-------------', data)
		self.buffer += data
	
	def handle_message (self, msg):
		self.msgs.append (msg)
				
	def found_terminator (self):
		if not self.buffer:
			return self.close ()
			
		buf, self.buffer = self.buffer, b""				
		if self._compressed is None:			
			self._compressed = struct.unpack ("!B", buf)[0]
			self.request.channel.set_terminator (4)
		
		elif self._msg_length == 0:
			self._msg_length = struct.unpack ("!I", buf)[0]
			self.request.channel.set_terminator (self._msg_length)
			if self._msg_length == 0:
				msg = decode_message (buf, self._compressed)
				self.handle_message (b"")
				self.request.channel.set_terminator (1)
				self._compressed = None
		
		else:			
			msg = decode_message (buf, self._compressed)
			self.request.channel.set_terminator (1)
			self._compressed = None
			self._msg_length = 0
			self.handle_message (msg)
						
		
class grpc_stream_collector (grpc_collector):
	def __init__ (self, handler, request, *args):
		grpc_collector.__init__ (self, handler, request, *args)
		self.producer = None
		self.send_stream = None
		self.lock = threading.Lock ()
				
	def start_collect (self):	
		self.request.channel.set_terminator (1)
		self.handler.continue_request (self.request, b"")				
	
	def handle_message (self, msg):
		self.msgs.append (msg)
		self.try_to_send ()
	
	def try_to_send (self):
		with self.lock:
			sendable = self.send_stream					
		if not sendable:
			return
		
		with self.lock:
			for msg in self.msgs:
				self.send_stream (msg)
			self.msgs = []
		
	def set_service (self, *args):		
		with self.lock:
			self.producer, self.send_stream = args		
		self.try_to_send ()
	
	def close (self):		
		self.send_stream (None) # stream end
		self.request.http2.stream_finished (self.request.stream_id)
	