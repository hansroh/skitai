import time
try:
	from h2.exceptions import FlowControlError
except ImportError:
	pass	

class h2header_producer:
	def __init__ (self, stream_id, headers, producer, encoder, lock):
		# DO NOT set self.stream_id
		# if set, priority_producer_fifo try to re-sort and will raise error
		with lock:
			encoder.send_headers (
				stream_id = stream_id,
				headers = headers,
				end_stream = producer is None
			)
			self.data_to_send = encoder.data_to_send ()
	
	def more (self):		
		data_to_send, self.data_to_send = self.data_to_send, b''
		return data_to_send

class h2stream_producer:
	BUFFER_SIZE = 4096	
	FLOW_CONTROL_WINDOW_UPDATE_TIMEOUT = 3
	
	def __init__ (self, stream_id, depends_on, weight, producer, encoder, lock):
		self.stream_id = stream_id
		self.depends_on = depends_on
		self.weight = weight
		self.producer = producer # globbing_producer
		self.encoder = encoder
		
		self._lock = lock
		self._buf = b""
		self._end_stream = False		
		self._last_sent = time.time ()
				
	def __repr__ (self):
		return "<h2stream_producer stream_id:%d, weight:%d, depends_on:%d>" % (self.stream_id, self.weight, self.depends_on)
	
	def is_done (self):
		return self._end_stream and not self._buf
			 	
	def more (self):
		if self.is_done ():
			return b''

		if self._buf:
			data, self._buf = self._buf [:self.BUFFER_SIZE], self._buf [self.BUFFER_SIZE:]
				
		else:
			data = self.producer.more ()
			self._end_stream = len (data) < self.producer.buffer_size
			if len (data) > self.BUFFER_SIZE:
				data, self._buf = data [:self.BUFFER_SIZE], data [self.BUFFER_SIZE:]
		
		# print ("MULTIPLEXING", self.stream_id, self.encoder.local_flow_control_window (self.stream_id))
		with self._lock:
			try:
				self.encoder.send_data (
					stream_id = self.stream_id,
					data = data,
					end_stream = self.is_done ()
				)
				self._last_sent = time.time ()	
				data_to_send = self.encoder.data_to_send ()
				
			except FlowControlError:
				# close forcely
				return b''
			
		return data_to_send
	
	def ready (self):
		# check if remote flow control window is open
		# if rfcw is 0, wait for FLOW_CONTROL_WINDOW_UPDATE_TIMEOUT to recieve WINDOW_UPDATE
		# but maybe unnecessory and unused
		with self._lock:
			lfcw = self.encoder.local_flow_control_window (self.stream_id)		
		if lfcw >= self.BUFFER_SIZE:
			return True		
		if time.time () - self._last_sent > self.FLOW_CONTROL_WINDOW_UPDATE_TIMEOUT:			
			return True
		return False
		