from skitai.lib import compressors
from collections import Iterable
import struct

class grpc_producer:
	def __init__ (self, msg = None):
		self.closed = False
		self.compressor = compressors.GZipCompressor ()
		self.message = msg		
	
	def serialize (self, msg):
		serialized = msg.SerializeToString ()
		compressed = 0
		if len (serialized) > 2048:
			serialized = self.compressor.compress (serialized) + self.compressor.flush ()
			compressed = 1						
		return struct.pack ("!B", compressed) + struct.pack ("!I", len (serialized)) + serialized
				
	def more (self):		
		if self.closed and not self.message:
			return b""
		
		if not isinstance (self.message, Iterable):
			msg = self.serialize (self.message)
			self.close ()			
			return msg
		
		try:
			msg = next (self.message)
			return self.serialize (msg)
		except StopIteration:
			self.close ()			
			return b""
		
	def close (self):		
		self.closed = True
		self.message = None
		

class grpc_stream_producer (grpc_producer):
	def __init__ (self):
		self.closed = False
		self.compressor = compressors.GZipCompressor ()
		self.messages = []
		
	def add_message (self, msg):
		self.messages.append (msg)
		
	def ready (self):
		return self.messages or self.closed
				
	def more (self):		
		while self.messages:
			first = self.messages [0]
			if not first:
				if first is None:
					self.close ()
					return b""
				else:
					del self.message [0]	
			
			if not isinstance (first, Iterable):				
				first = self.messages.pop (0)
				return self.serialize (first)
				
			if type (fisrt) is list:
				first = self.messages.pop (0)
				first = iter (first)
				self.messages.insert (0, first)
			
			try:
				msg = next (first)
				return self.serialize (msg)
			except StopIteration:
				self.message.pop (0)
				continue				
		
	def close (self):		
		self.closed = True
		self.messages = []

