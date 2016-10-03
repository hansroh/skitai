from . import wsgi_handler
import skitai
from skitai.lib import producers
from h2.connection import H2Connection, GoAwayFrame
from h2.exceptions import ProtocolError, NoSuchStreamError
from h2.events import DataReceived, RequestReceived, StreamEnded, PriorityUpdated, ConnectionTerminated, StreamReset, WindowUpdated
from h2.errors import PROTOCOL_ERROR, FLOW_CONTROL_ERROR
from .http2.request import request as http2_request
from .http2.vchannel import fake_channel, data_channel
from .http2.producers import h2stream_producer, h2header_producer
from .http2.fifo import priority_producer_fifo
import threading
try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO


class http2_request_handler:
	collector = None
	producer = None
	http11_terminator = 24
	def __init__ (self, handler, request):
		self.handler = handler
		self.wasc = handler.wasc
		self.request = request
		self.channel = request.channel
		
		self.channel.producer_fifo = priority_producer_fifo ()
		
		self.conn = H2Connection(client_side = False)
		self.frame_buf = self.conn.incoming_buffer
		self.frame_buf.max_frame_size = self.conn.max_inbound_frame_size
		
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

		self._plock = threading.Lock () # for self.conn
		self._clock = threading.Lock () # for self.x
		
	def close_when_done (self, errcode = 0, msg = None):
		with self._plock:
			self.conn.close_connection (errcode, msg)
		self.send_data ()
		self.channel.close_when_done ()		
			
	def close (self, force = False):
		if self._closed: return
		self._closed = True		
		if force:
			self.channel = None
			
		if self.channel:
			with self._plock:
				self.conn.close_connection () # go_away
			self.send_data ()
			
		self.handler.finish_request (self.request)
		
	def closed (self):
		return self._closed
			
	def send_data (self):
		with self._plock:
			data_to_send = self.conn.data_to_send ()
		
		if data_to_send:
			#print ("SEND", repr (data_to_send), len (data_to_send))
			self.channel.push (data_to_send)
	
	def handle_preamble (self):
		if self.request.version.startswith ("2."):
			self.channel.set_terminator (6) # SM\r\n\r\n
					
	def initiate_connection (self):
		self.handle_preamble ()
		h2settings = self.request.get_header ("HTTP2-Settings")
		if h2settings:
			self.conn.initiate_upgrade_connection (h2settings)
		else:	
			self.conn.initiate_connection()		
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
		with self._plock:
			events = self.conn._receive_frame (self.current_frame)
		return events

	def set_terminator (self, terminator):
		self.channel.set_terminator (terminator)
					
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
			#print ("++FRAME", self.current_frame, '::', self.data_length)
						
			if self.data_length == 0:
				events = self.set_frame_data (b'')
			self.channel.set_terminator (self.data_length == 0 and 9 or self.data_length)	# next frame header
			
		else:
			raise ProtocolError ("Frame decode error")
		
		if events:
			self.handle_events (events)
	
	def get_new_stream_id (self):
		with self._clock:
			self._send_stream_id += 2
			stream_id = self._send_stream_id
		return stream_id
		
	def push_promise (self, stream_id, request_headers, addtional_request_headers):
		promise_stream_id = self.get_new_stream_id ()
		with self._clock:
			self.promises [promise_stream_id] = request_headers	+ addtional_request_headers	
		
		with self._plock:
			self.conn.push_stream (stream_id, promise_stream_id, request_headers	+ addtional_request_headers)
		self.send_data ()
					
	def push_response (self, stream_id, headers, producer):
		#print ("++RESPONSE", headers)
		with self._clock:
			r = self.requests [stream_id]
			try:
				depends_on, weight = self.priorities [stream_id]
			except KeyError:
				depends_on, weight = 0, 1	
			else:
				del self.priorities [stream_id]				
		
		self.channel.push_with_producer (
			h2header_producer (stream_id, headers, producer, self.conn, self._plock)
		)
		if producer:
			outgoing_producer = h2stream_producer (
				stream_id, depends_on, weight, producer, self.conn, self._plock
			)			
			self.channel.push_with_producer (outgoing_producer)
			
			r.http2 = None # break bacj ref.
			with self._clock:
				#self.channel.ready = self.channel.producer_fifo.ready
				del self.requests [stream_id]
			
		promise_stream_id, promise_headers = None, None
		with self._clock:
			try: promise_stream_id, promise_headers = self.promises.popitem ()
			except KeyError: pass
		
		if promise_stream_id:
			self.handle_request (promise_stream_id, promise_headers, is_promise = True)
		
	def handle_events (self, events):
		for event in events:
			#print ('++EVENT', event)
			if isinstance(event, RequestReceived):
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
				
			elif isinstance(event, PriorityUpdated):
				if event.exclusive:
					# rebuild depend_ons
					for stream_id in list (self.priorities.keys ()):
						depends_on, weight = self.priorities [stream_id]
						if depends_on == event.depends_on:
							self.priorities [stream_id] = [event.stream_id, weight]
					
				with self._clock:
					self.priorities [event.stream_id] = [event.depends_on, event.weight]
				
			elif isinstance(event, DataReceived):
				with self._clock:
					r = self.requests [event.stream_id]
				r.channel.set_data (event.data, event.flow_controlled_length)
				r.channel.handle_read ()
				
			elif isinstance(event, StreamEnded):
				r = None
				with self._clock:
					try: r = self.requests [event.stream_id]
					except KeyError: pass
				
				if r and r.collector:
					# unexpected end of body
					r.http2 = None # break back ref.
					with self._clock:
						del self.requests [event.stream_id]
					with self._plock:
						self.close_when_done (PROTOCOL_ERROR)
						return
			
		self.send_data ()
							
	def handle_request (self, stream_id, headers, is_promise = False):
		#print ("++REQUEST: %d" % stream_id, headers)
		command = "GET"
		uri = "/"
		scheme = "http"
		authority = ""
		cl = 0
		h = []
		cookies = []
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
			elif k == "cookie":
				cookies.append (v)
				continue					
			h.append ("%s: %s" % (k, v))
								
		if cookies:
			h.append ("Cookie: %s" % "; ".join (cookies))
			
		should_have_collector = False	
		if command == "CONNECT":
			first_line = "%s %s HTTP/2.0" % (command, authority)
			vchannel = self.channel			
		else:	
			first_line = "%s %s HTTP/2.0" % (command, uri)
			if command in ("POST", "PUT"):
				should_have_collector = True
				vchannel = data_channel (self.channel, cl)
			else:
				vchannel = fake_channel (self.channel)
		
		r = http2_request (self, vchannel, first_line, command.lower (), uri, "2.0", scheme, h, stream_id, is_promise)		
		vchannel.current_request = r
		
		with self._clock:
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
					if should_have_collector and cl > 0 and r.collector is None:
						# too large body
						with self._plock:						
							self.conn.reset_stream (stream_id, FLOW_CONTROL_ERROR)
						self.send_data ()	
						# some browser ignore reset, why?
						self.close_when_done (FLOW_CONTROL_ERROR)
						
					elif cl > 0:
						# give permission for sending data to a client
						with self._plock:
							self.conn.increment_flow_control_window (cl)
							rfcw = self.conn.remote_flow_control_window (stream_id)
							if cl > rfcw:
								self.conn.increment_flow_control_window (cl - rfcw, stream_id)
						self.send_data ()	
							
				return					
					
		try: r.response.error (404)
		except: pass


class h2_request_handler (http2_request_handler):
	http11_terminator = None
	
	def handle_preamble (self):
		if self.request.version.startswith ("2."):
			self.conn.receive_data ("PRI * HTTP/2.0\r\n\r\n")
			self.channel.set_terminator (None)
			
	def collect_incoming_data (self, data):		
		with self._plock:
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
		
		http2 = http2_request_handler (self, request)		
		request.channel.add_closing_partner (http2)
		request.channel.set_response_timeout (self.keep_alive)
		request.channel.set_keep_alive (self.keep_alive)
		
		if request.version == "1.1":
			request.response (
				"101 Switching Protocol",
				headers = [("Connection",  "upgrade"), ("Upgrade", "h2c"), ("Server", skitai.NAME.encode ("utf8"))]
			)
			request.response.done (False, False, False, (http2, http2.http11_terminator))
		
		else:
			request.channel.current_request = http2
			
		http2.initiate_connection ()
		
	def finish_request (self, request):
		if request.channel:
			request.channel.close_when_done ()
			
	