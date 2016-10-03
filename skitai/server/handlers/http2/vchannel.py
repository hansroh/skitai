import asynchat

class fake_channel:
	def __init__ (self, channel):
		# override members
		self._channel = channel
		self.addr = channel.addr
		self.connected = channel.connected
	
	def __getattr__ (self, attr):
		return getattr (self._channel, attr)


class data_channel (fake_channel, asynchat.async_chat):
	def __init__ (self, channel, content_length):
		asynchat.async_chat.__init__ (self)
		fake_channel.__init__ (self, channel)
		self._content_length = content_length
		self._data = b""		
		self._data_size = 0
		self._chunks  = []
			
	def set_data (self, data, size):
		self._data = data
		self._data_size += size
		self._chunks.append (size)			
	
	def get_chunk_size (self):
		d = {}
		for c in self._chunks:
			d [c] = None
		return len (d) == 1 and c
			
	def get_data_size (self):
		return self._data_size

	def get_content_length (self):
		return self._content_length
		
	def recv (self, buffer_size):
		data, self._data = self._data, b""
		return data
				
	def collect_incoming_data (self, data):		
		self.current_request.collect_incoming_data (data)
	
	def found_terminator (self):
		self.current_request.found_terminator ()
		