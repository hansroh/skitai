from skitai.lib import producers, compressors
import struct
from collections import Iterable

class grpc_producer (producers.iter_producer):		
	def __init__ (self, data):
		producers.iter_producer.__init__ (self, data)
		self.compressor = compressors.GZipCompressor ()
		
	def more (self):		
		try:
			data = next (self.data)
			serialized = data.SerializeToString ()
			compressed = 0
			if len (serialized) > 2048:
				data = self.compressor.compress (serialized) + self.compressor.flush ()
				compressed = 1
			return struct.pack ("<B", compressed) + struct.pack ("<i", len (serialized)) + serialized			
		except StopIteration:			
			return b""
	
	@classmethod
	def get_messages (cls, fp):
		decompressor = None	
		msgs = []
		byte = fp.read (1)
		while byte:
			iscompressed = struct.unpack ("<B", byte) [0]
			length = struct.unpack ("<i", fp.read (4)) [0]
			msg = fp.read (length)
			if iscompressed:
				if decompressor is None:
					decompressor = compressors.GZipDecompressor ()
				msg = decompressor.deconpress (msg)	+ decompressor.flush ()
			byte = fp.read (1)
			msgs.append (msg)
		return msgs
		