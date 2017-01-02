from . import base_request_handler
from h2.connection import H2Connection, GoAwayFrame
from h2.exceptions import ProtocolError, NoSuchStreamError
from h2.events import DataReceived, ResponseReceived, StreamEnded, ConnectionTerminated, StreamReset, WindowUpdated
from h2.errors import PROTOCOL_ERROR, FLOW_CONTROL_ERROR
from skitai.lib.producers import simple_producer
from skitai.server.handlers.http2.producers import h2stream_producer, h2header_producer
try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO

class FakeCon:
	def __init__ (self):
		pass


class RequestHandler (base_request_handler.RequestHandler):
	faskecon = FakeCon ()
		
	def __init__ (self, handler):
		self.asyncon = handler.asyncon		
		self.logger = handler.request.logger
		self.lock = handler.asyncon.lock # pool lock
		self._clock = threading.RLock () # conn lock
		self._llock = threading.RLock () # local lock
		
		self._send_stream_id = 1
		self.requests = {}
		self.add_request (1, handler)						
		
		self.conn = H2Connection (client_side = True)
		self.buf = b""
		self.rfile = BytesIO ()
		self.frame_buf = self.conn.incoming_buffer
		self.frame_buf.max_frame_size = self.conn.max_inbound_frame_size		
		self.data_length = 0
		self.current_frame = None
		
		self.conn.initiate_connection()
		self.send_data ()
		self.asyncon.set_terminator (9)
		self.asyncon.set_active (False)
	
	def add_request (self, stream_id, handler):
		handler.asyncon = self.faskecon
		with self._llock:
			self.requests [stream_id] = handler
				
	def get_new_stream_id (self):
		with self._llock:
			self._send_stream_id += 2
			stream_id = self._send_stream_id
		return stream_id
	
	def send_data (self):
		with self._llock:
			data_to_send = self.conn.data_to_send ()		
		if data_to_send:			
			with self.lock:
				self.asyncon.push (data_to_send)
			
	def handle_request (self, handler):
		self.asyncon.set_active (False)
		stream_id = self.get_new_stream_id ()
		header, payload = handler.get_request_header (), handler.get_request_payload ()
		if payload:
			producer = simple_producer (payload)
		header = h2header_producer (stream_id, header, producer, self.conn, self._clock)
		payload = h2stream_producer (stream_id, 0, 1, producer, self.conn, self._clock)
		
		self.add_request (stream_id, handler)
		with self._llock:
			self.asyncon.push (header)		
			self.asyncon.push (payload)
	
	def collect_incoming_data (self, data):
		if not data:
			return
			
		if self.data_length:
			self.rfile.write (data)
		else:
			self.buf += data
	
	def connection_closed (self):
		with self._llock:
			for stream_id, request in self.requests.items ():
				request.connection_closed ()
			self.requests = {}	
										
	def found_terminator (self):
		buf, self.buf = self.buf, b""
		
		events = None
		if self.data_length:			
			events = self.set_frame_data (self.rfile.getvalue ())				
			self.data_length = 0
			self.current_frame = None
			self.rfile.seek (0)
			self.rfile.truncate ()
			self.channel.set_terminator (9) # for frame header
						
		elif buf:
			self.current_frame, self.data_length = self.frame_buf._parse_frame_header (buf)
			self.frame_buf.max_frame_size = self.conn.max_inbound_frame_size
			self.frame_buf._validate_frame_length (self.data_length)			
						
			if self.data_length == 0:
				events = self.set_frame_data (b'')
			self.set_terminator (self.data_length == 0 and 9 or self.data_length)	# next frame header
			
		else:
			raise ProtocolError ("Frame decode error")
		
		if events:
			self.handle_events (events)	
	
	def set_frame_data (self, data):
		if not self.current_frame:
			return []
		self.current_frame.parse_body (memoryview (data))				
		self.current_frame = self.frame_buf._update_header_buffer (self.current_frame)
		with self._plock:
			events = self.conn._receive_frame (self.current_frame)
		return events
	
	def handle_events (self, events):
		for event in events:
			#print ('++EVENT', event)
			if isinstance(event, ResponseReceived):
				self.handle_request (event.stream_id, event.headers)				
					
			elif isinstance(event, StreamReset):
				if event.remote_reset:
					deleted = False
					if event.stream_id % 2 == 0: # promise stream
						with self._clock:
							try: del self.promises [event.stream_id]
							except KeyError: pass
							else: deleted = True
					
					if not deleted:
						self.channel.producer_fifo.remove (event.stream_id)
						
			elif isinstance(event, ConnectionTerminated):
				self.close (True)
				
			elif isinstance(event, DataReceived):
				with self.llock:	
					h = self.requests [event.stream_id]
				h.collect_incoming_data (event.data)
				h.handle_read ()
				h.callback (h)
				
			elif isinstance(event, StreamEnded):
				r = None
				with self.llock:
					try: h = self.requests [event.stream_id]
					except KeyError: pass
				
		self.send_data ()
