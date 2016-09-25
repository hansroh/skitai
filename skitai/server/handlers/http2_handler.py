from . import wsgi_handler
from skitai.lib import producers
from h2.connection import H2Connection, GoAwayFrame
from h2.exceptions import ProtocolError, NoSuchStreamError
from h2.events import DataReceived, RequestReceived, StreamEnded, PriorityUpdated, ConnectionTerminated, StreamReset, WindowUpdated
from h2.errors import PROTOCOL_ERROR, FLOW_CONTROL_ERROR
from . import http2
from .http2.fifo import priority_producer_fifo
import threading
try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO


class HTTP2:
	collector = None
	producer = None
	
	def __init__ (self, handler, request):
		self.handler = handler
		self.wasc = handler.wasc
		self.request = request
		self.channel = request.channel
		
		self.channel.producer_fifo = priority_producer_fifo ()
		
		self.conn = H2Connection(client_side = False)
		self.frame_buf = self.conn.incoming_buffer
		self.frame_buf.max_frame_size = self.conn.max_inbound_frame_size
		self.initiate_connection ()
		
		self.data_length = 0
		self.current_frame = None
		self.rfile = BytesIO ()
		self.buf = b""

		self.requests = {}
		self.priorities = {}
		self.promises = {}
		
		self._send_stream_id = 0
		self._closed = False
		self._got_preamble = False		

		self._plock = threading.Lock ()
		self._clock = threading.Lock ()
		self._alock = threading.Lock ()
	
	def close_when_done (self):
		# send go_away b'\x00\x00\x08\x07\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x00\x00\x00\x00')		
		self.channel.push (GoAwayFrame (stream_id = 0).serialize ())
		self.channel.close_when_done ()
			
	def close (self, force = False):
		if self._closed: return
		self._closed = True		
		if force:
			self.channel = None
			
		if self.channel:
			self.conn.close_connection () # go_away
			self.send_data ()
			
		self.handler.finish_request (self.request)
		
	def closed (self):
		return self._closed
			
	def send_data (self, stream_id = 0):					
		data_to_send = self.conn.data_to_send ()
		if data_to_send:
			#print ("SEND", repr (data_to_send), len (data_to_send), '::', self.channel.get_terminator ())		
			self.channel.push (data_to_send)
	
	def handle_preamble (self):
		if self.request.version == "1.1":
			self.channel.push (
				b"HTTP/1.1 101 Switching Protocols\r\nconnection: upgrade\r\nupgrade: h2c\r\n\r\n"
			)			
			self.channel.set_terminator (24) # PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n
		else:
			self.channel.set_terminator (6) # SM\r\n\r\n
					
	def initiate_connection (self):		
		self.handle_preamble ()	
		h2settings = self.request.get_header ("HTTP2-Settings")
		if h2settings:
			self.conn.initiate_upgrade_connection (h2settings)
		else:	
			self.conn.initiate_connection()		
		#self.conn.update_settings ({INITIAL_WINDOW_SIZE: 12451840})
		self.send_data ()
		
		if self.request.version == "1.1":
			headers = [
				(":method", self.request.command.upper ()), 
				(":path", self.request.uri),
			]
			for line in self.request.get_header ():
				k, v = line.split (": ", 1) 
				k = k.lower ()
				if k in ("http2-settings", "connection", "upgrade"):
					continue
				headers.append ((k, v))		
			self.handle_request (1, headers)
			
	def collect_incoming_data (self, data):
		#print ("RECV", repr (data), len (data), '::', self.channel.get_terminator ())		
		if not data:
			# closed connection
			self.close (True)
			return
			
		if self.data_length:
			self.rfile.write (data)
		else:
			self.buf += data
	
	def set_frame_data (self, data):
		if not self.current_frame:
			return []
		self.current_frame.parse_body (memoryview (data))			
		self.current_frame = self.frame_buf._update_header_buffer (self.current_frame)
		events = self.conn._receive_frame (self.current_frame)
		return events
					
	def found_terminator (self):
		buf, self.buf = self.buf, b""
		
		#print ("FOUND", repr (buf), '::', self.data_length, self.channel.get_terminator ())		
		events = None
		if not self._got_preamble:
			if not buf.endswith (b"SM\r\n\r\n"):
				raise ProtocolError ("Invalid preamble")
			self.channel.set_terminator (9)
			self._got_preamble = True
			
		elif self.data_length:			
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
			#print ("FRAME", self.current_frame, '::', self.data_length)
						
			if self.data_length == 0:
				events = self.set_frame_data (b'')
			self.channel.set_terminator (self.data_length == 0 and 9 or self.data_length)	# next frame header
			
		else:
			raise ProtocolError ("Frame decode error")
		
		if events:
			self.handle_events (events)
	
	def get_new_stream_id (self):
		with self._alock:
			self._send_stream_id += 2
			stream_id = self._send_stream_id
		return stream_id
		
	def push_promise (self, stream_id, request_headers, addtional_request_headers):
		promise_stream_id = self.get_new_stream_id ()
		with self._alock:
			self.promises [promise_stream_id] = request_headers	+ addtional_request_headers	
		
		with self._plock:
			self.conn.push_stream (stream_id, promise_stream_id, request_headers	+ addtional_request_headers)
		self.send_data (stream_id)
					
	def push_response (self, stream_id, headers, producer):
		with self._clock:
			try:
				depends_on, weight = self.priorities [stream_id]
			except KeyError:
				depends_on, weight = 0, 1	
			else:
				del self.priorities [stream_id]	
		
		with self._clock:
			r = self.requests [stream_id]
		r.http2 = None # break bacj ref.
		
		self.channel.push_with_producer (
			producers.h2header_producer (stream_id, headers, producer, self.conn, self._plock)
		)
		if producer:
			outgoing_producer = producers.h2stream_producer (
				stream_id, depends_on, weight, producer, self.conn, self._plock
			)			
			
			self.channel.ready = self.channel.producer_fifo.ready
			self.channel.push_with_producer (outgoing_producer)
			with self._clock:
				del self.requests [stream_id]
			
		promise_stream_id, promise_headers = None, None
		with self._alock:
			try: promise_stream_id, promise_headers = self.promises.popitem ()
			except KeyError: pass
		if promise_stream_id:
			self.handle_request (promise_stream_id, promise_headers, is_promise = True)
	
	def push_promised_data (self, stream_id):
		if stream_id % 2 != 0 or stream_id == 0:
			return			
		r = None
		with self._clock:
			try: r = self.requests [stream_id]
			except KeyError: pass
		if r is None or not r.is_promise or r.outgoing_producer is None:
			return
		
		r.outgoing_producer.depends_on, r.outgoing_producer.weight = self.priorities [stream_id]
		self.channel.ready = self.channel.producer_fifo.ready
		self.channel.push_with_producer (r.outgoing_producer)
		r.outgoing_producer = None			
		
	def handle_events (self, events):
		for event in events:
			#print ('EVENT', event)
			if isinstance(event, RequestReceived):
				self.handle_request (event.stream_id, event.headers)				
					
			elif isinstance(event, StreamReset):
				if event.remote_reset:
					deleted = False
					if event.stream_id % 2 == 0: # promise stream
						with self._alock:
							try: del self.promises [event.stream_id]
							except KeyError: pass
							else: deleted = True
					
					if not deleted:
						self.channel.producer_fifo.remove (event.stream_id)
						
			elif isinstance(event, ConnectionTerminated):
				self.close (True)
				
			elif isinstance(event, PriorityUpdated):
				if event.exclusive:
					# rebuild depend_ons
					for stream_id in list (self.priorities.keys ()):
						depends_on, weight = self.priorities [stream_id]
						if depends_on == event.depends_on:
							self.priorities [stream_id] = [event.stream_id, weight]
					
				with self._clock:
					self.priorities [event.stream_id] = [event.depends_on, event.weight]
					
				#self.push_promised_data (event.stream_id)	
				
			elif isinstance(event, DataReceived):
				with self._clock:
					r = self.requests [event.stream_id]
				r.channel.set_data (event.data, event.flow_controlled_length)
				r.channel.handle_read ()
				
				chnk = r.channel.get_chunk_size ()
				rfcw = self.conn.remote_flow_control_window (event.stream_id)
				ctln = r.channel.get_content_length ()
				dtln = r.channel.get_data_size ()				
				if rfcw == 0 or (chnk and event.flow_controlled_length == chnk and rfcw < chnk):
					remains = ctln - dtln
					if remains:
						self.conn.increment_flow_control_window (remains, event.stream_id)
						self.conn.increment_flow_control_window (ctln)
						
			elif isinstance(event, StreamEnded):
				r = None
				with self._clock:
					try: r = self.requests [event.stream_id]
					except KeyError: pass
				
				if r and r.collector:
					with self._clock:
						del self.requests [event.stream_id]
					self.conn.reset_stream (event.stream_id, PROTOCOL_ERROR)
					self.close ()
					return
			
			elif isinstance(event, WindowUpdated):
				#self.push_promised_data (event.stream_id)				
				pass
		
		try: 			
			self.send_data (event.stream_id)
		except AttributeError:
			self.send_data ()	
							
	def handle_request (self, stream_id, headers, is_promise = False):
		#print ("REQUEST: %d" % stream_id, headers)
		command = "GET"
		uri = "/"
		scheme = "http"
		authority = ""
		
		h = []
		cl = None
		
		for k, v in headers:
			if k[0] == ":":
				if k == ":method": command = v
				elif k == ":path": uri = v
				elif k == ":scheme": scheme = v
				elif k == ":authority":
					authority = v
					if authority:
						h.append ("host: %s" % authority)				
				continue
			if k == "content-length":
				cl = int (v)
			h.append ("%s: %s" % (k, v))
		
		should_have_collector = False					
		if command == "CONNECT":
			first_line = "%s %s HTTP/2.0" % (command, authority)
			vchannel = self.channel			
		else:	
			first_line = "%s %s HTTP/2.0" % (command, uri)
			if command in ("POST", "PUT"):
				should_have_collector = True
				vchannel = http2.data_channel (self.channel, cl)
			else:
				vchannel = http2.fake_channel (self.channel)
		
		r = http2.request (self, vchannel, first_line, command.lower (), uri, "2.0", scheme, h, stream_id, is_promise)		
		vchannel.current_request = r
		self.channel.request_counter.inc()
		self.channel.server.total_requests.inc()
		
		for h in self.channel.server.handlers:
			if h.match (r):
				with self._clock:
					self.requests [stream_id] = r
						
				try:
					h.handle_request (r)
					
				except:
					self.channel.server.trace()
					try: r.response.error (500)
					except: pass
						
				else:					
					if should_have_collector and r.collector is None:
						# content-length validated
						#self.close () # graceful disconnect
						self.conn.reset_stream (stream_id, FLOW_CONTROL_ERROR)
						self.close ()					
					return					
					
		try: r.response.error (404)
		except: pass


class HTTP2h2 (HTTP2):
	def handle_preamble (self):
		if self.request.version == "1.1":
			self.channel.push (
				b"HTTP/1.1 101 Switching Protocols\r\nconnection: upgrade\r\nupgrade: h2c\r\n\r\n"
			)
		else:				
			self.conn.receive_data (b"PRI * HTTP/2.0\r\n\r\n")
		self.channel.set_terminator (None) # PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n
			
	def collect_incoming_data (self, data):		
		events = self.conn.receive_data (data)
		self.handle_events (events)


class Handler (wsgi_handler.Handler):
	keep_alive = 120
	
	def match (self, request):
		if request.command == "pri" and request.uri == "*" and request.version == "2.0":
			return True
		if request.command in ('post', 'put'):
			return False
		upgrade = request.get_header ("upgrade")
		return upgrade and upgrade.lower () == "h2c" and request.version == "1.1" and request.command == "get"
	
	def handle_request (self, request):
		http2 = HTTP2 (self, request)		
		
		if request.channel:
			request.channel.add_closing_partner (http2)
			request.channel.current_request = http2
			request.channel.set_response_timeout (self.keep_alive)
			request.channel.set_keep_alive (self.keep_alive)
		
	def finish_request (self, request):
		if request.channel:
			request.channel.close_when_done ()
			
	