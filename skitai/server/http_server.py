#!/usr/bin/env python

import sys
import asyncore, asynchat
import re, socket, time, threading, os
from . import http_date, http_response, producers, utility, counter
from .threads import threadlib
from skitai import lifetime
import zlib, gzip, io
from . import compressors
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
		self.response = http_response.http_response (self)
		self.body = None
		self.reply_code = 200
		self.reply_message = ""		
		self._split_uri = None
		self._header_cache = {}
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
	
	def get_raw_header (self):
		return self.header	
	get_headers = get_raw_header
	
	path_regex = re.compile (r'([^;?#]*)(;[^?#]*)?(\?[^#]*)?(#.*)?')
	def split_uri (self):
		if self._split_uri is None:
			m = self.path_regex.match (self.uri)
			if m.end() != len(self.uri):
				raise ValueError("Broken URI")
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
		if header not in hc:
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
	
	def get_content_type (self):
		return self.get_header_with_params ("content-type") [0]
				
	def get_main_type (self):
		ct = self.get_header_with_params ("content-type")
		if ct is None:
			return
		return ct.split ("/", 1) [0]
	
	def get_sub_type (self):
		ct = self.get_header_with_params ("content-type")
		if ct is None:
			return
		return ct.split ("/", 1) [1]
		
	def get_user_agent (self):
		return self.get_header ("user-agent")
	
	def get_remote_addr (self):
		return self.channel.addr [0]
			
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
	closed = False
	is_rejected = False
	abortables = []
	zombie_timeout = MAX_KEEP_CONNECTION
	
	def __init__ (self, server, conn, addr):
		self.channel_number = http_channel.channel_count.inc ()
		self.request_counter = counter.counter()
		self.bytes_out = counter.counter()
		
		asynchat.async_chat.__init__ (self, conn)		
		self.server = server
		self.addr = addr		
		self.set_terminator (b'\r\n\r\n')
		self.in_buffer = b''
		self.creation_time = int (time.time())
		self.event_time = int (time.time())
		
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
				return b""			
			return result
			
		except MemoryError:
			lifetime.shutdown (1, 1)
			
	def collect_incoming_data (self, data):
		#print ("collect_incoming_data", repr (data [:180]))
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
			self.in_buffer = b''
			
			lines = header.decode ("utf8").split('\r\n')
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
		if self.closed:
			return
		self.closed = True	
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
	
	def trace (self, id = None):
		self.server.trace (id)
			
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
			if os.name == "nt":
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
	