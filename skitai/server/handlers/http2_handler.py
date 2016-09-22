from . import wsgi_handler
from skitai.server import http_request, http_response
from skitai.lib import producers, compressors
from skitai.server.threads import trigger
import asynchat
from h2.connection import H2Connection, INITIAL_WINDOW_SIZE
from h2.exceptions import ProtocolError
from h2.events import DataReceived, RequestReceived, StreamEnded, PriorityUpdated, ConnectionTerminated, StreamReset
from h2.errors import PROTOCOL_ERROR, FLOW_CONTROL_ERROR
import threading
try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO


class priority_producer_fifo:
	def __init__ (self):
		self.l = []
		self._lock = threading.Lock ()
	
	def __len__ (self):
		with self._lock:
			l = len (self.l)
		return l
		
	def __getitem__(self, index):
		with self._lock:
			i = self.l [index]
		return i	
	
	def __setitem__(self, index, item):
		with self._lock:
			self.l.insert (index, item)
		
	def __delitem__ (self, index):	
		with self._lock:
			del self.l [index]
		
	def append (self, item):
		if item is None:
			with self._lock:
				self.l.append (item)
			return
				
		try:
			w1 = item.weight
			d1 = item.depends_on
		except AttributeError:
			with self._lock:
				self.l.append (item)
			return
		
		index = 0
		inserted = False
		with self._lock:
			for each in self.l:
				try:
					w2 = each.weight
					d2 = each.depends_on
				except AttributeError:
					pass
				else:
					if d2 >= d1 and w2 < w1:
						self.l.insert (index, item)
						inserted = True
						break
				index += 1
		
		if not inserted:
			with self._lock:
				self.l.append (item)
		
		#with self._lock:
		#	print ('+++++++++++++++++', self.l)
			
	def appendleft (self, item):
		with self._lock:
			self.l.insert (0, item)
		
	def clear (self):
		with self._lock:
			self.l = []
			
			
class http2_response (http_response.http_response):
	USE_DATA_COMPRESS = True
	
	def __init__ (self, request):
		http_response.http_response.__init__ (self, request)
	
	def push (self, thing):
		if not self.responsable (): return
		if type(thing) is bytes:			
			self.outgoing.push (producers.simple_producer (thing))
		else:
			self.outgoing.push (thing)
			
	def build_reply_header (self):	
		h = [(b":status", str (self.reply_code).encode ("utf8"))]
		for k, v in self.reply_headers:
			h.append ((k.encode ("utf8"), str (v).encode ("utf8")))		
		return h
	
	def push_promise (self, promised_stream_id, headers):
		self.request.http2.push_promise (self.request.stream_id, promised_stream_id, headers)
		
	def done (self, *args, **karg):
		# removed by HTTP/2.0 Spec.
		self.delete ('transfer-encoding')
		self.delete ('connection')
		
		if len (self.outgoing) == 0:
			outgoing_producer = None
		
		else:
			way_to_compress = ""
			if self.USE_DATA_COMPRESS and not self.has_key ('Content-Encoding'):
				maybe_compress = self.request.get_header ("Accept-Encoding")
				if maybe_compress and self.has_key ("content-length") and int (self ["Content-Length"]) <= http_response.UNCOMPRESS_MAX:
					maybe_compress = ""
				else:	
					content_type = self ["Content-Type"]
					if maybe_compress and content_type and (content_type.startswith ("text/") or content_type.endswith ("/json-rpc")):
						accept_encoding = [x.strip () for x in maybe_compress.split (",")]
						if "gzip" in accept_encoding:
							way_to_compress = "gzip"
						elif "deflate" in accept_encoding:
							way_to_compress = "deflate"
			
				if way_to_compress:
					if self.has_key ('Content-Length'):
						self.delete ("content-length") # rebuild
					self.update ('Content-Encoding', way_to_compress)
			
			if way_to_compress:
				if way_to_compress == "gzip":
					producer = producers.gzipped_producer
				else: # deflate
					producer = producers.compressed_producer
				outgoing_producer = producer (producers.composite_producer (self.outgoing))						
			else:
				outgoing_producer = producers.composite_producer (self.outgoing)		
			
			outgoing_producer = producers.globbing_producer (producers.hooked_producer (outgoing_producer, self.log))
		
		try:
			self.request.http2.push_response (
				self.request.stream_id, 
				self.build_reply_header (), 
				outgoing_producer
			)
		
		except:
			self.request.logger.trace ()			
			self.request.http2.close (True)
			
		
class http2_request (http_request.http_request):
	def __init__ (self, *args):
		self.request_number = self.request_count.inc()		
		(self.http2, self.channel, self.request,		 
		 self.command, self.uri, self.version,
		 self.header, 
		 self.stream_id) = args
		
		self.logger = self.channel.server.server_logger
		self.server_ident = self.channel.server.SERVER_IDENT
		self.body = None
		self.reply_code = 200
		self.reply_message = ""		
		self._split_uri = None
		self._header_cache = {}
		self.gzip_encoded = False
		self.response = http2_response (self)


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

		self.stream_data = {}
		self.stream_weights = {}	
		
		self._closed = False
		self._got_preamble = False		

		self._plock = threading.Lock ()
		self._clock = threading.Lock ()
		
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
			
	def send_data (self):			
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
		return self.conn._receive_frame (self.current_frame)
		
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
	
	def push_promise (self, stream_id, promised_stream_id, request_headers):
		self.conn.push_stream (stream_id, promised_stream_id, request_headers)
		self.send_data ()
					
	def push_response (self, stream_id, headers, producer):
		with self._clock:
			try:
				depends_on, weight = self.stream_weights [stream_id]
			except KeyError:
				depends_on, weight = 0, 1
		
		#import random
		#weight = random.randrange (1, 256)		
		outgoing_producer = producers.h2stream_producer (stream_id, depends_on, weight, headers, producer, self.conn, self._plock)		
		
		with self._clock:
			try:
				del self.stream_weights [stream_id]		
			except KeyError:
				pass
							
			r = None
			try:
				r = self.stream_data [stream_id]
			except KeyError:
				pass
			else:
				del self.stream_data [stream_id]
		
			if r:
				r.http2 = None # break bacj ref.				
		
		self.channel.push_with_producer (outgoing_producer)
		
	def handle_events (self, events):
		for event in events:
			#print ('EVENT', event)
			if isinstance(event, RequestReceived):
				self.handle_request (event.stream_id, event.headers)				
				
			elif isinstance(event, ConnectionTerminated):
				self.close (True)
				
			elif isinstance(event, PriorityUpdated):
				if event.exclusive:
					# rebuild depend_ons
					with self._clock:
						for stream_id in list (self.stream_weights.keys ()):
							depends_on, weight = self.stream_weights [stream_id]
							if depends_on == event.depends_on:
								self.stream_weights [stream_id] = [event.stream_id, weight]
																					
				with self._clock:
					self.stream_weights [event.stream_id] = [event.depends_on, event.weight]			
				
			elif isinstance(event, DataReceived):
				r = None
				with self._clock:
					try:
						r = self.stream_data [event.stream_id]
					except KeyError:
						pass
				
				# POST, PUT method
				if r:
					r.channel.set_data (event.data, event.flow_controlled_length)
					r.channel.handle_read ()
					
					chnk = r.channel.get_chunk_size ()
					rfcw = self.conn.remote_flow_control_window (event.stream_id)
					ctln = r.channel.get_content_length ()
					dtln = r.channel.get_data_size ()
					
					#print ("---data / chunk / remote_window_size", event.flow_controlled_length, chnk, rfcw)
					if rfcw == 0 or (chnk and event.flow_controlled_length == chnk and rfcw < chnk):
						remains = ctln - dtln
						if remains:
							#print ("### WINDOW UPDATE", remains)
							self.conn.increment_flow_control_window (remains, event.stream_id)
							self.conn.increment_flow_control_window (ctln)
							#print ('~~~~~~~~~~', remains, ctln)
					
			elif isinstance(event, StreamEnded):
				r = None
				with self._clock:
					try:
						r = self.stream_data [event.stream_id]
					except KeyError:
						# GET,... method												
						pass
				
				if r and r.collector:
					self.conn.reset_stream (event.stream_id, PROTOCOL_ERROR)
					self.close ()
					return
					
					with self._clock:
						del self.stream_data [event.stream_id]
					self.stream_lengths [event.stream_id]
					
		self.send_data ()
			
	def handle_request (self, stream_id, headers):
		command = "GET"
		uri = "/"
		h = []
		cl = None
		for k, v in headers:
			if k[0] == ":":
				if k == ":method": command = v
				elif k == ":path": uri = v
				elif k == ":authority": h.append ("host: %s" % v)
				continue
			if k == "content-length":
				cl = int (v)
			h.append ("%s: %s" % (k, v))
		
		should_have_collector = False		
		if command in ("POST", "PUT"):
			should_have_collector = True
			vchannel = data_channel (self.channel, cl)			
		else:
			vchannel = fake_channel (self.channel)			
		
		r = http2_request (self, vchannel, "%s %s HTTP/2.0" % (command, uri), command.lower (), uri, "2.0", h, stream_id)
		vchannel.current_request = r
		self.channel.request_counter.inc()
		self.channel.server.total_requests.inc()
		
		for h in self.channel.server.handlers:
			if h.match (r):						
				try:
					h.handle_request (r)
				except:
					self.channel.server.trace()
					try: r.response.error (500)
					except: pass
				else:
					if r:
						if should_have_collector and r.collector is None:
							# content-length validated
							#self.close () # graceful disconnect
							self.conn.reset_stream (stream_id, FLOW_CONTROL_ERROR)
							self.close ()
							return
							
						if r.collector:
							with self._clock:
								self.stream_data [stream_id] = r
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
			
	