#!/usr/bin/env python

import sys
import asyncore, asynchat
import re, socket, time, threading, os
import http_date, producers, utility, counter
from threads import threadlib
from types import StringTypes
from skitai import lifetime
import zlib, gzip, cStringIO
import compressors
import signal
import ssl
from skitai import VERSION

MAX_KEEP_CONNECTION = 60 * 30
PID = []
ACTIVE_WORKERS = 0
SURVAIL = True
EXITCODE = 0

class http_request:
	version = "1.1"
	collector = None
	producer = None
	request_count = counter.counter()
	
	def __init__ (self, *args):		
		self.request_number = self.request_count.inc()		
		(self.channel, self.request,
		 self.command, self.uri, self.version,
		 self.header) = args
		self.logger = self.channel.server.server_logger
		self.server_ident = self.channel.server.SERVER_IDENT

		self.reply_headers = [
			('Server', "sae"),
			('Date', http_date.build_http_date (time.time()))
			]
		
		self.body = None
		self.reply_code = 200
		self.reply_message = ""
		self.outgoing = producers.fifo ()
		self._split_uri = None
		self._header_cache = {}
		self.requeststr = ''
		self.gzip_encoded = False
		self.set_keep_alive ()
	
	def set_keep_alive (self):
		keep_alive = None		
		try:
			keep_alive = int (self.get_header ("keep-alive"))
		except (ValueError, TypeError):
			return
		else:
			if keep_alive > MAX_KEEP_CONNECTION: keep_alive = MAX_KEEP_CONNECTION
			self.channel.zombie_timeout = keep_alive
		
	def __setitem__ (self, key, value):
		self.reply_headers.append ((key, value))

	def __getitem__ (self, key):
		key = key.lower ()
		for k, v in self.reply_headers:
			if k.lower () == key:
				return v
	
	def delete (self, k):
		index = 0
		found = 0
		k = k.lower ()
		for hk, hv in self.reply_headers:
			if k == hk.lower ():
				found = 1
				break
			index += 1
		
		if found:
			del self.reply_headers [index]
			self.delete (k)
		
	def update (self, k, v):
		self.delete (k)
		self [k] = v
		
	def has_key (self, key):
		key = key.lower ()
		return key in map (lambda x: x [0].lower (), self.reply_headers)
		
	def get_raw_header (self):
		return self.header	
	get_headers = get_raw_header		
			
	def build_reply_header (self):		
		return '\r\n'.join (
			[self.response(self.reply_code, self.reply_message)] + map (
				lambda x: '%s: %s' % x,
				self.reply_headers
				)
			) + '\r\n\r\n'

	path_regex = re.compile (r'([^;?#]*)(;[^?#]*)?(\?[^#]*)?(#.*)?')
	def split_uri (self):
		if self._split_uri is None:
			m = self.path_regex.match (self.uri)
			if m.end() != len(self.uri):
				raise ValueError, "Broken URI"
			else:
				self._split_uri = m.groups()				
		return self._split_uri

	def get_header_with_regex (self, head_reg, group):
		for line in self.header:
			m = head_reg.match (line)
			if m.end() == len(line):
				return head_reg.group (group)
		return ''
	
	def set_body (self, body):
		self.body = body
	
	def get_body (self):
		return self.body
			
	def get_header (self, header):
		header = header.lower()
		hc = self._header_cache
		if not hc.has_key (header):
			h = header + ':'
			hl = len(h)
			for line in self.header:
				if line [:hl].lower() == h:
					r = line [hl:].strip ()
					hc [header] = r
					return r
			hc [header] = None
			return None
		else:
			return hc[header]

	def collect_incoming_data (self, data):
		if self.collector:
			self.collector.collect_incoming_data (data)			
		else:
			self.logger.log (
				'dropping %d bytes of incoming request data' % len(data),
				'warning'
				)

	def found_terminator (self):
		if self.collector:
			self.collector.found_terminator()			
		else:
			self.logger.log (
				'unexpected end-of-record for incoming request',
				'warning'
				)
	
	def push (self, thing):
		if self.channel is None: return		
		if type(thing) == type(''):
			self.outgoing.push (producers.simple_producer (thing))
		else:
			self.outgoing.push (thing)
			
	def response (self, code, msg):
		if not msg:
			try:
				msg = self.responses [code]
			except KeyError: 
				msg = "Undefined"	
		return 'HTTP/%s %d %s' % (self.version, code, msg)
	
	def set_reply_code (self, code, msg = ""):
		self.reply_code = code
		self.reply_message = msg
	
	def instant (self, code):
		if self.version != "1.1": return		
		message = self.responses [code]
		self.channel.push (self.response (code, message) + "\r\n\r\n")
	
	def abort (self, code):
		self.channel.reject ()
		message = self.responses [code]
		self.error (code, message, force_close = True)
		
	def error (self, code, detail = "", force_close = False):
		self.reply_code = code
		message = self.responses [code]
		if not detail:
			detail = message

		s = self.DEFAULT_ERROR_MESSAGE % {
			'code': code,
			'message': message,
			'info': detail
		}
		
		self.update ('Content-Length', len(s))
		self.update ('Content-Type', 'text/html')
		self.delete ('content-encoding')
		self.delete ('expires')
		self.delete ('cache-control')
		self.delete ('set-cookie')
		
		self.push (s)
		self.done (True, True, force_close)

	# can also be used for empty replies
	reply_now = error
	
	def done (self, globbing = True, compress = True, force_close = False):
		if self.channel is None: return
			
		connection = utility.get_header (utility.CONNECTION, self.header).lower()
		close_it = False
		way_to_compress = ""
		wrap_in_chunking = False
		
		if force_close:
			close_it = True
		
		else:
			if self.version == '1.0':
				if connection == 'keep-alive':
					if not self.has_key ('Content-Length'):
						close_it = True
				else:
					close_it = True
			
			elif self.version == '1.1':
				if connection == 'close':
					close_it = True
				elif not self.has_key ('Content-Length'):
					wrap_in_chunking = True
					
			elif self.version is None:
				close_it = True
		
		if close_it:
			self.update ('Connection', 'close')
		else:
			self.update ('Connection', 'keep-alive')
			
		if compress and not self.has_key ('Content-Encoding'):
			maybe_compress = self.get_header ("Accept-Encoding")
			if maybe_compress and self.has_key ("Content-Length") and self ["Content-Length"] < 1024:
				maybe_compress = ""
			
			else:	
				content_type = self ["Content-Type"]
				if maybe_compress and content_type and (content_type.startswith ("text/") or content_type.endswith ("/json-rpc")):
					accept_encoding = map (lambda x: x.strip (), maybe_compress.split (","))
					if "gzip" in accept_encoding:
						way_to_compress = "gzip"
					elif "deflate" in accept_encoding:
						way_to_compress = "deflate"
		
			if way_to_compress:
				if self.has_key ('Content-Length'):
					self.delete ("Content-Length") # rebuild
					wrap_in_chunking = True
				self.update ('Content-Encoding', way_to_compress)
		
		if wrap_in_chunking:
			self.delete ('Content-Length')
			self.update ('Transfer-Encoding', 'chunked')
			
			if way_to_compress:
				if way_to_compress == "gzip": 
					producer = producers.gzipped_producer
				else: # deflate
					producer = producers.compressed_producer
				outgoing_producer = producer (producers.composite_producer (self.outgoing))
				
			else:
				outgoing_producer = producers.composite_producer (self.outgoing)				
				
			outgoing_producer = producers.chunked_producer (outgoing_producer)
			outgoing_header = producers.simple_producer (self.build_reply_header())
			outgoing_producer = producers.composite_producer (
				producers.fifo([outgoing_header, outgoing_producer])
			)
			
		else:
			self.delete ('Transfer-Encoding')
			
			if way_to_compress:
				if way_to_compress == "gzip":
					compressor = compressors.GZipCompressor ()
				else: # deflate
					compressor = zlib.compressobj (6, zlib.DEFLATED)
				
				cdata = ""
				has_producer = 1
				while 1:
					has_producer, producer = self.outgoing.pop ()
					if not has_producer: break
					cdata += compressor.compress (producer.data)				
				cdata += compressor.flush ()
				
				self.update ("Content-Length", len (cdata))
				self.outgoing = producers.fifo ([producers.simple_producer (cdata)])
			
			outgoing_header = producers.simple_producer (self.build_reply_header())
			self.outgoing.push_front (outgoing_header)
			outgoing_producer = producers.composite_producer (self.outgoing)
		
		try:
			if globbing:				
				self.channel.push_with_producer (producers.globbing_producer (producers.hooked_producer (outgoing_producer, self.log)))
			else:
				self.channel.push_with_producer (producers.hooked_producer (outgoing_producer, self.log))
			
			self.channel.current_request = None
			# proxy collector and producer is related to asynconnect
			# and relay data with channel
			# then if request is suddenly stopped, make sure close them
			self.channel.abort_when_close ([self.collector, self.producer])
			if close_it:
				self.channel.close_when_done()
		
		except:
			self.logger.trace ()
			self.logger.log (
				'channel maybe closed',
				'warning'
			)						
			
	def log (self, bytes):		
		self.channel.server.log_request (
			'%s:%d %s %s %s %d'
			% (self.channel.addr[0],
			self.channel.addr[1],			
			self.request,
			self.requeststr,
			self.reply_code,			
			bytes)
			)
	
	responses = {
		100: "Continue",
		101: "Switching Protocols",
		200: "OK",
		201: "Created",
		202: "Accepted",
		203: "Non-Authoritative Information",
		204: "No Content",
		205: "Reset Content",
		206: "Partial Content",
		300: "Multiple Choices",
		301: "Moved Permanently",
		302: "Moved Temporarily",
		303: "See Other",
		304: "Not Modified",
		305: "Use Proxy",
		400: "Bad Request",
		401: "Unauthorized",
		402: "Payment Required",
		403: "Forbidden",
		404: "Not Found",
		405: "Method Not Allowed",
		406: "Not Acceptable",
		407: "Proxy Authentication Required",
		408: "Request Time-out",
		409: "Conflict",
		410: "Gone",
		411: "Length Required",
		412: "Precondition Failed",
		413: "Request Entity Too Large",
		414: "Request-URI Too Large",
		415: "Unsupported Media Type",
		500: "Internal Server Error",
		501: "Not Implemented",
		502: "Bad Gateway",
		503: "Service Unavailable",
		504: "Gateway Time-out",
		505: "HTTP Version not supported",
		506: "Proxy Error"
		}

	# Default error message
	DEFAULT_ERROR_MESSAGE = '\r\n'.join (
		[
		 '<!DOCTYPE html>',
		 '<html>',
		 '<head>',
		 '<title>%(code)d %(message)s</title>',
		 '<style>',
		 'body, p {font-family: "arial"; font-size: 12px;}',
		 'h1 {font-family: "arial black"; font-weight: bold; font-size: 24px;}',		 
		 '</style>',
		 '</head>',
		 '<body>',
		 '<h1>%(code)d %(message)s</h1>',
		 '<p>Error code %(code)d.',
		 '<br>Message: %(message)s.',		 
		 '<p><strong>%(info)s</strong>',
		 '</body>',
		 '</html>',
		 ''
		 ]
		)



#-------------------------------------------------------------------
# server channel
#-------------------------------------------------------------------
class http_channel (asynchat.async_chat):
	ac_out_buffer_size = 4096
	ac_in_buffer_size = 4096
	current_request = None
	channel_count = counter.counter ()
	ready = None
	affluent = None
	abortables = []
	zombie_timeout = MAX_KEEP_CONNECTION
	
	def __init__ (self, server, conn, addr):
		self.channel_number = http_channel.channel_count.inc ()
		self.request_counter = counter.counter()
		self.bytes_out = counter.counter()
		
		asynchat.async_chat.__init__ (self, conn)		
		self.server = server
		self.addr = addr		
		self.set_terminator ('\r\n\r\n')
		self.in_buffer = ''
		self.creation_time = int (time.time())
		self.event_time = int (time.time())
		self.is_rejected = False
		
	def reject (self):
		self.is_rejected = True		
		
	def readable (self):
		if self.affluent is not None:
			return not self.is_rejected and asynchat.async_chat.readable (self)	and self.affluent ()
		return not self.is_rejected and asynchat.async_chat.readable (self)
			
	def writable (self):
		if self.ready is not None:
			return asynchat.async_chat.writable (self) and self.ready ()
		return asynchat.async_chat.writable (self)
		
	def issent (self):
		return self.bytes_out.as_long ()
		
	def __repr__ (self):
		ar = asynchat.async_chat.__repr__(self) [1:-1]
		return '<%s channel#: %s requests:%s>' % (
				ar,
				self.channel_number,
				self.request_counter
				)
		
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 3:			
			self.reject ()			
			if self.writable ():
				return 1
			else:				
				self.close ()
				return 0				
		return 0

	def isconnected (self):
		return self.connected
	
	def handle_timeout (self):
		self.log ("zombie channel %s killed." % ":".join (map (str, self.addr)))
		self.close ()
				
	def send (self, data):
		self.event_time = int (time.time())
		result = asynchat.async_chat.send (self, data)
		self.server.bytes_out.inc (result)
		self.bytes_out.inc (result)
		return result
	
	def recv (self, buffer_size):
		self.event_time = int (time.time())
		
		try:
			result = asynchat.async_chat.recv (self, buffer_size)
			self.server.bytes_in.inc (len (result))
			if not result:
				self.handle_close ()
				return ""			
			return result
			
		except MemoryError:
			lifetime.shutdown (1, 1)
		
	def collect_incoming_data (self, data):
		if self.current_request:			
			self.current_request.collect_incoming_data (data)
		else:			
			self.in_buffer = self.in_buffer + data
				
	def found_terminator (self):
		if self.is_rejected:
			return
			
		if self.current_request:			
			self.current_request.found_terminator()
			
		else:
			header = self.in_buffer
			self.in_buffer = ''
			lines = header.split('\r\n')
			
			while lines and not lines[0]:
				lines = lines[1:]

			if not lines:
				self.close_when_done()
				return

			request = lines[0]
			try:
				command, uri, version = utility.crack_request (request)							
			except:
				self.log_info ("channel-%s invaild request header" % self.channel_number, "fail")
				return self.close ()			
				
			header = utility.join_headers (lines[1:])
			
			r = http_request (self, request, command, uri, version, header)
			
			self.request_counter.inc()
			self.server.total_requests.inc()
			
			if command is None:
				r.error (400)
				return
			
			for h in self.server.handlers:
				if h.match (r):
					try:
						self.current_request = r
						h.handle_request (r)
						
					except:						
						self.server.trace()
						try: r.error (500)
						except: pass
					return
					
			r.error (404)
	
	def abort_when_close (self, things):
		self.abortables = things
					
	def close (self):
		if self.current_request is not None:		
			self.abortables.append (self.current_request.collector)
			self.abortables.append (self.current_request.producer)
			self.current_request.channel = None # break circ refs
			self.current_request = None
			
		for abortable in self.abortables:
			if abortable:
				abortable.abort ()
		
		self.discard_buffers ()
		asynchat.async_chat.close (self)
		self.connected = False		
			
	def log (self, message, type = "info"):
		self.server.log (message, type)
		
	def log_info (self, message, type='info'):
		self.server.log (message, type)
		
	def handle_expt(self):
		self.log_info ("channel-%s panic" % self.channel_number, "fail")
		self.close ()
			
	def handle_error (self):
		self.server.trace ("channel-%s" % self.channel_number)		
		self.close()
	
		
#-------------------------------------------------------------------
# server class
#-------------------------------------------------------------------
class http_server (asyncore.dispatcher):
	SERVER_IDENT = 'sae %s' % VERSION
	def __init__ (self, ip, port, server_logger = None, request_logger = None):
		global PID
		self.handlers = []
		self.ip = ip
		self.port = port
		self.ssl_ctx = None
		asyncore.dispatcher.__init__ (self)
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)		
		self.set_reuse_addr ()
		self.bind ((ip, port))
		
		self.worker_ident = "master"
		self.server_logger = server_logger
		self.request_logger = request_logger
		self.start_time = time.ctime(time.time())
		self.start_time_int = time.time()
		
		self.total_clients = counter.mpcounter()
		self.total_requests = counter.mpcounter()
		self.exceptions = counter.mpcounter()
		self.bytes_out = counter.mpcounter()
		self.bytes_in  = counter.mpcounter()
		
		host, port = self.socket.getsockname()
		if not ip:
			ip = socket.gethostname()			
		try:
			ip = socket.gethostbyname (ip)
			self.server_name = socket.gethostbyaddr (ip)[0]
		except socket.error:			
			self.server_name = ip		
		self.server_port = port
	
	def set_ssl_ctx (self, ssl_ctx):
		self.ssl_ctx = ssl_ctx
		
	def fork_and_serve (self, numworker = 1):
		global ACTIVE_WORKERS, SURVAIL, PID, EXITCODE
		
		child = 0	
		self.listen (os.name == "posix" and 65535 or 256)
		
		if os.name == "posix":
			while SURVAIL:
				if ACTIVE_WORKERS < numworker:
					pid = os.fork ()
					if pid == 0:				
						self.worker_ident = "worker #%d" % len (PID)
						PID = []
						signal.signal(signal.SIGTERM, hTERMWORKER)
						signal.signal(signal.SIGQUIT, hQUITWORKER)
						break
					else:
						PID.append (pid)
						ACTIVE_WORKERS += 1
						signal.signal(signal.SIGHUP, hHUPMASTER)
						signal.signal(signal.SIGTERM, hTERMMASTER)
						signal.signal(signal.SIGQUIT, hQUITMASTER)
						signal.signal (signal.SIGCHLD, hCHLD)
				time.sleep (1)
			
			if self.worker_ident == "master":
				return EXITCODE
				
		else:
			signal.signal(signal.SIGTERM, hTERMWORKER)			
				
		self.log_info ('%s (%s) started on %s:%d' % (
			self.SERVER_IDENT, self.worker_ident, self.server_name, self.port)
		)
		
	def create_socket(self, family, type):
		if hasattr (socket, "_no_timeoutsocket"):
			sock_class = socket._no_timeoutsocket
		else:
			sock_class = socket.socket

		self.family_and_type = family, type
		sock = sock_class (family, type)
		sock.setblocking(0)
		self.set_socket(sock)
	
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 2:
			if self.worker_ident != "parent":
				self.log_info ('abandon listening socket %s' % self.server_name)
				self.del_channel ()
			else:	
				self.log_info ('closing %s' % self.server_name)
				self.close ()
				
	def writable (self):
		return 0

	def install_handler (self, handler, back = 1):
		if back:
			self.handlers.append (handler)
		else:
			self.handlers.insert (0, handler)

	def remove_handler (self, handler):
		self.handlers.remove (handler)
	
	def log (self, message, type = "info"):
		if self.server_logger:
			self.server_logger.log (message, type)
		else:
			sys.stdout.write ('log: [%s] %s\n' % (type,str (message)))	
	
	def log_request (self, message):
		if self.request_logger:
			self.request_logger.log (message)
		else:
			sys.stdout.write ('%s\n' % message)
	
	def log_info(self, message, type='info'):
		self.log (message, type)
	
	def trace (self, id = None):
		self.exceptions.inc()
		if self.server_logger:
			self.server_logger.trace (id)
		else:
			asyncore.dispatcher.handle_error (self)
	
	def handle_read (self):
		pass

	def readable (self):
		return self.accepting
	
	def handle_error (self):
		self.trace()		
		
	def handle_connect (self):
		pass

	def handle_accept (self):
		self.total_clients.inc()
		try:
			conn, addr = self.accept()		
		except socket.error:
			self.log_info ('server accept() threw an exception', 'warn')
			return
		except TypeError:
			self.log_info ('server accept() threw EWOULDBLOCK', 'warn')
			return
		#self.log_info ('client %s:%d accepted by %s' % (addr [0], addr [1], self.worker_ident))
		http_channel (self, conn, addr)
		
	def handle_expt (self):
		self.log_info ('socket panic', 'warning')
	
	def handle_close (self):
		self.log_info('server shutdown', 'warning')
		self.close()
	
	def status(self):
		global PID
		return 	{
			"child_pids": PID,
			"ident": "%s for %s" % (self.worker_ident, self.SERVER_IDENT),
			"start_time": self.start_time, 			
			"port": self.port,
			"total_clients": self.total_clients.as_long(),
			"total_request": self.total_requests.as_long(), 
			"total_exceptions": self.exceptions.as_long(), 
			"bytes_out": self.bytes_out.as_long(), 
			"bytes_in": self.bytes_in.as_long()
		}
			
def hCHLD (signum, frame):
	global ACTIVE_WORKERS
	ACTIVE_WORKERS -= 1
	os.wait ()

def hTERMWORKER (signum, frame):			
	lifetime.shutdown (0, 1)

def hQUITWORKER (signum, frame):			
	lifetime.shutdown (0, 0)
	
def DO_SHUTDOWN (sig):
	global SURVAIL, PID
	SURVAIL = False	
	signal.signal (signal.SIGCHLD, signal.SIG_IGN)
	for pid in PID:
		try: os.kill (pid, sig)
		except OSError: pass
			
def hTERMMASTER (signum, frame):		
	global EXITCODE
	EXITCODE = 0
	DO_SHUTDOWN (signal.SIGTERM)

def hQUITMASTER (signum, frame):
	global EXITCODE
	EXITCODE = 0
	DO_SHUTDOWN (signal.SIGQUIT)

def hHUPMASTER (signum, frame):		
	global EXITCODE
	EXITCODE = 3
	DO_SHUTDOWN (signal.SIGTERM)


		
if __name__ == "__main__":
	pass
	