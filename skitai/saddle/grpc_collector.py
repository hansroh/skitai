from skitai.server.handlers.collectors import FormCollector
from skitai.server import counter
from collections import Iterable
from aquests.protocols.grpc.message import decode_message
import struct
import time

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
