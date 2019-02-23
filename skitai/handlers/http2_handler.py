from . import wsgi_handler
import skitai
from rs4 import producers
from h2.connection import H2Connection, GoAwayFrame, DataFrame, H2Configuration
from h2.exceptions import ProtocolError, NoSuchStreamError, StreamClosedError
from h2.events import TrailersReceived, DataReceived, RequestReceived, StreamEnded, PriorityUpdated, ConnectionTerminated, StreamReset, WindowUpdated, RemoteSettingsChanged
from h2.settings import SettingCodes
from h2.errors import ErrorCodes
from rs4 import producers
from .http2.request import request as http2_request
from .http2.vchannel import fake_channel, data_channel
from aquests.protocols.http2.producers import h2header_producer, h2frame_producer
from aquests.protocols.http2.fifo import http2_producer_fifo, http2_producer_ts_fifo
from aquests.protocols.http2.request_handler import FlowControlWindow
import threading
from io import BytesIO

class http2_request_handler (FlowControlWindow):
	collector = None
	producer = None
	http11_terminator = 24
	
	def __init__ (self, handler, request):
		self.handler = handler
		self.wasc = handler.wasc
		self.request = request
		self.channel = request.channel
		
		# replace fifo with supporting priority, ready, removing
		if self.wasc.numthreads:
			self.channel.producer_fifo = http2_producer_ts_fifo ()
		else:	
			self.channel.producer_fifo = http2_producer_fifo ()
		
		self.conn = H2Connection (H2Configuration (client_side = False))
		self.frame_buf = self.conn.incoming_buffer
		self.frame_buf.max_frame_size = self.conn.max_inbound_frame_size
		
		self.data_length = 0
		self.current_frame = None
		self.rfile = BytesIO ()
		self.buf = b""

		self.requests = {}
		self.priorities = {}
		self.promises = {}
		
		self._closed = False
		self._got_preamble = False		
		
		self._plock = threading.Lock () # for self.conn
		self._clock = threading.Lock () # for self.x
				
	def close (self, errcode = 0, msg = None):
		if self._closed: return
		self._closed = True		
		if self.channel:
			self.go_away (errcode) # go_away
		
		with self._clock:	
			stream_ids = list (self.requests.keys ())		
		for stream_id in stream_ids:
			self.remove_request (stream_id)
	
	def enter_shutdown_process (self):
		self.close (ErrorCodes.NO_ERROR)
			
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
			self.handle_request (1, self.upgrade_header ())			
			
	def upgrade_header (self):
		headers = [
			(":method", self.request.command.upper ()), 
			(":path", self.request.uri),
		]
		for line in self.request.get_header ():
			try:
				k, v = line.split (": ", 1) 
			except ValueError:
				k, v = line.split (":", 1) 	
			k = k.lower ()
			if k in ("http2-settings", "connection", "upgrade"):
				continue
			headers.append ((k, v))		
		return headers
					
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
		#print ("FOUND", self.request.version, self.request.command, self.data_length)
		events = None	
		if self.request.version == "1.1" and self.data_length:
			self.request.version = "2.0" # upgrade
			data = self.rfile.getvalue ()
			with self._clock:
				r = self.requests [1]				
			r.channel.set_data (data, len (data))
			r.set_stream_ended ()
			self.data_length = 0
			self.rfile.seek (0)
			self.rfile.truncate ()			
			self.channel.set_terminator (24) # for premble
		
		elif not self._got_preamble:			
			if not buf.endswith (b"SM\r\n\r\n"):
				raise ProtocolError ("Invalid preamble")
			self._got_preamble = True
			self.channel.set_terminator (9)
		
		elif self.data_length:
			events = self.set_frame_data (self.rfile.getvalue ())
			self.current_frame = None
			self.data_length = 0
			self.rfile.seek (0)
			self.rfile.truncate ()			
			self.channel.set_terminator (9) # for frame header
									
		elif buf:
			self.current_frame, self.data_length = self.frame_buf._parse_frame_header (buf)
			self.frame_buf.max_frame_size = self.data_length
			
			if self.data_length == 0:
				events = self.set_frame_data (b'')
			self.channel.set_terminator (self.data_length == 0 and 9 or self.data_length)	# next frame header
			
		else:
			raise ProtocolError ("Frame decode error")
		
		if events:
			self.handle_events (events)
	
	def pushable (self):
		return self.conn.remote_settings [SettingCodes.ENABLE_PUSH]
			
	def push_promise (self, stream_id, request_headers, addtional_request_headers):		
		promise_stream_id = self.conn.get_next_available_stream_id ()		
		with self._clock:
			self.promises [promise_stream_id] = request_headers	+ addtional_request_headers		
		with self._plock:			
			self.conn.push_stream (stream_id, promise_stream_id, request_headers	+ addtional_request_headers)
	
	def handle_response (self, stream_id, headers, trailers, producer, do_optimize, force_close = False):
		with self._clock:
			if self.promises:
				self.send_data ()
			
		r = self.get_request (stream_id)
		with self._clock:
			try:
				depends_on, weight = self.priorities [stream_id]
			except KeyError:
				depends_on, weight = 0, 1	
			else:
				del self.priorities [stream_id]
		
		header_producer = h2header_producer (stream_id, headers, producer or trailers, self.conn, self._plock)		
		if not producer:
			header_producer = r.response.log_or_not (r.uri, header_producer, r.response.log)			
			self.channel.push_with_producer (header_producer)
			
		else:
			self.channel.push_with_producer (header_producer)
			outgoing_producer = r.response.log_or_not (r.uri, producer, r.response.log)
			
			if do_optimize:
				outgoing_producer = producers.globbing_producer (outgoing_producer)
			
			outgoing_producer = h2frame_producer (
				stream_id, depends_on, weight, outgoing_producer, self.conn, self._plock, trailers
			)
			# is it proper?
			#outgoing_producer = producers.ready_globbing_producer (outgoing_producer)
			self.channel.push_with_producer (outgoing_producer)
		
		if r.is_stream_ended ():
			# needn't recv data any more
			self.remove_request (stream_id)
		
		if force_close:
			return self.go_away (ErrorCodes.CANCEL)
				
		current_promises = []
		with self._clock:
			while self.promises:
				current_promises.append (self.promises.popitem ())				
		for promise_stream_id, promise_headers in current_promises:
			self.handle_request (promise_stream_id, promise_headers)			

	def remove_request (self, stream_id):
		r = self.get_request (stream_id)
		if not r: return
		with self._clock:
			try: del self.requests [stream_id]
			except KeyError: pass		
		r.http2 = None
		
	def get_request (self, stream_id):
		r = None
		with self._clock:
			try: r =	self.requests [stream_id]
			except KeyError: pass
		return r
	
	def adjust_flow_control_window (self, stream_id):
		if self.conn.inbound_flow_control_window < self.MIN_IBFCW:			
			with self._clock:
				self.conn.increment_flow_control_window (1048576)
				
		rfcw = self.conn.remote_flow_control_window (stream_id)
		if rfcw < self.MIN_RFCW:
			try:
				with self._clock:
					self.conn.increment_flow_control_window (1048576, stream_id)
			except StreamClosedError:
				pass
			
	def handle_events (self, events):
		for event in events:
			#print (event)
			if isinstance(event, RequestReceived):				
				self.handle_request (event.stream_id, event.headers)				
				
			elif isinstance(event, TrailersReceived):
				self.handle_trailers (event.stream_id, event.headers)
					
			elif isinstance(event, StreamReset):
				if event.remote_reset:
					r = self.get_request (event.stream_id)
					if r and r.collector:
						try: r.collector.stream_has_been_reset ()
						except AttributeError: pass
						r.set_stream_ended ()
						
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
				r = self.get_request (event.stream_id)				
				if not r:
					self.go_away (ErrorCodes.PROTOCOL_ERROR)
				else:
					try:
						r.channel.set_data (event.data, event.flow_controlled_length)
					except ValueError:						
						# from vchannel.handle_read () -> collector.collect_inconing_data ()
						self.go_away (ErrorCodes.CANCEL)
					else:
						self.adjust_flow_control_window (event.stream_id)
					
			elif isinstance(event, StreamEnded):
				r = self.get_request (event.stream_id)
				if r:
					if r.collector:
						r.channel.handle_read ()
						r.channel.found_terminator ()					
					r.set_stream_ended ()
					if r.response.is_done ():
						# DO NOT REMOVE before responsing
						# this is for async streaming request like proxy request
						self.remove_request (event.stream_id)
					
		self.send_data ()
	
	def go_away (self, errcode = 0, msg = None):
		with self._plock:
			self.conn.close_connection (errcode, msg)
		self.send_data ()
		self.channel.close_when_done ()
	
	def reset_stream (self, stream_id, errcode = ErrorCodes.CANCEL):
		closed = False
		with self._plock:
			try:
				self.conn.reset_stream (stream_id, error_code = errcode)
			except StreamClosedError:	
				closed = True
		if not closed:		
			self.send_data ()
		self.remove_request (stream_id)
		#self.request.logger ("stream reset (stream_id:%d, error:%d)" % (stream_id, errcode), "info")
	
	def handle_trailers	 (self, stream_id, headers):
		r = self.get_request (stream_id)
		for k, v in headers:
			r.header.append (
				"{}: {}".format (k.decode ("utf8"), v.decode ("utf8"))
			)
		
	def handle_request (self, stream_id, headers):		
		#print ("++REQUEST: %d" % stream_id, headers)
		command = "GET"
		uri = "/"
		scheme = "http"
		authority = ""
		cl = 0
		h = []
		cookies = []
		
		if type (headers [0][0]) is bytes:
			headers = [(k.decode ("utf8"), v.decode ("utf8")) for k, v in headers]
			
		for k, v in headers:
			#print ('HEADER:', k, v)
			if k[0] == ":":
				if k == ":method": command = v.upper ()
				elif k == ":path": uri = v
				elif k == ":scheme": scheme = v.lower ()
				elif k == ":authority":
					authority = v
					if authority:
						h.append ("host: %s" % authority.lower ())				
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
				vchannel = data_channel (stream_id, self.channel, cl)
			else:
				if stream_id == 1:
					self.request.version = "2.0"
				vchannel = fake_channel (stream_id, self.channel)

		r = http2_request (
			self,  scheme, stream_id, 
			vchannel, first_line, command.lower (), uri, "2.0", h
		)
		vchannel.current_request = r		
		with self._clock:
			self.channel.request_counter.inc()
			self.channel.server.total_requests.inc()
		
		h = self.handler.default_handler
		if not h.match (r):
			try: r.response.error (404)			
			except: pass
			return	
			
		with self._clock:
			self.requests [stream_id] = r

		try:					
			h.handle_request (r)
			
		except:
			self.channel.server.trace()
			try: r.response.error (500)
			except: pass
				
		else:
			if should_have_collector and cl > 0:
				if r.collector is None:
					# POST but too large body or 3xx, 4xx
					if stream_id == 1 and self.request.version == "1.1":						
						self.channel.close_when_done ()
						self.remove_request (1)
					else:						
						self.go_away (ErrorCodes.PROTOCOL_ERROR)
				else:							
					if stream_id == 1 and self.request.version == "1.1":
						self.data_length = cl
						self.set_terminator (cl)

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
	
	def __init__(self, wasc, default_handler = None):
		wsgi_handler.Handler.__init__(self, wasc, None)
		self.default_handler = default_handler
		
	def match (self, request):
		return True
		
	def handle_request (self, request):
		is_http2 = False
		if request.command == "pri" and request.uri == "*" and request.version == "2.0":
			is_http2 = True
		else:	
			upgrade = request.get_header ("upgrade")		
			is_http2 = upgrade and upgrade.lower () == "h2c" and request.version == "1.1"

		if not is_http2:
			return self.default_handler.handle_request (request)
	
		http2 = http2_request_handler (self, request)		
		request.channel.die_with (http2, "http2 stream")
		request.channel.set_socket_timeout (self.keep_alive)
		
		if request.version == "1.1":
			request.response (
				"101 Switching Protocol",
				headers = [("Connection",  "upgrade"), ("Upgrade", "h2c"), ("Server", skitai.NAME.encode ("utf8"))]
			)
			request.response.done (upgrade_to = (http2, http2.http11_terminator))
		
		else:
			request.channel.current_request = http2
			
		http2.initiate_connection ()
	