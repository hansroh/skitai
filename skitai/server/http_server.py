#!/usr/bin/env python

import sys
import asyncore, asynchat
import re, socket, time, threading, os
from . import http_date, http_request, utility, counter
from .threads import threadlib
from skitai import lifetime
from skitai.lib import producers, compressors
import signal
import ssl
from skitai import VERSION
import skitai

PID = []
ACTIVE_WORKERS = 0
SURVAIL = True
EXITCODE = 0
DEBUG = False

	
#-------------------------------------------------------------------
# server channel
#-------------------------------------------------------------------
class http_channel (asynchat.async_chat):	
	current_request = None
	channel_count = counter.counter ()
	ready = None
	affluent = None
	closed = False
	is_rejected = False
	
	zombie_timeout = 5
	keep_alive = 5
	response_timeout = 10
	
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
		self.__history = []
		
		self.closable_producers = []
		self.closable_partners = []
	
	def get_history (self):
		return self.__history
			
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
			self.close ()
			return 0
	      		
	def isconnected (self):
		return self.connected
	
	def handle_timeout (self):
		self.log ("killing zombie channel %s" % ":".join (map (str, self.addr)))
		if not self.closable_partners:
			self.close ()
			return
		
		# for graceful shutdown for partners	
		for closable in self.closable_partners:
			if closable and hasattr (closable, "close"):
				try:
					closable.close ()
				except:
					self.server.trace()

		self.closable_partners = []
		if len (self.producer_fifo) and self.producer_fifo [-1] is not None:
			# not be called close_when_done, then close forcely
			self.close ()
	
	def set_response_timeout (self, timeout):
		self.response_timeout = timeout
	
	def set_keep_alive (self, timeout):
		self.keep_alive = timeout	
		
	def set_timeout_by_case (self):
		if self.affluent or self.ready:
			self.zombie_timeout = self.response_timeout * 2
		else:	
			self.zombie_timeout = self.response_timeout
		
	def handle_read (self):
		self.set_timeout_by_case ()
		asynchat.async_chat.handle_read (self)
		
	def handle_write (self):
		self.set_timeout_by_case ()
		asynchat.async_chat.handle_write (self)		
	
	def initiate_send (self):
		ret = asynchat.async_chat.initiate_send (self)		
		if len (self.producer_fifo) == 0:
			self.done_request ()
		return ret	
	
	def add_closable_producer (self, thing):
		self.closable_producers.append (thing)
	
	def add_closing_partner (self, thing):
		self.closable_partners.append (thing)
		
	def done_request (self):	
		self.zombie_timeout = self.keep_alive
		self.closable_producers = [] # all producers are finished
		self.ready = None
		self.affluent = None
							
	def send (self, data):
		#print	("SEND", str (data), self.get_terminator ())
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
			#print	("RECV", repr(result), self.get_terminator ())
			return result
			
		except MemoryError:
			lifetime.shutdown (1, 1)
				
	def collect_incoming_data (self, data):
		#print ("collect_incoming_data", repr (data [:180]), self.current_request)
		if self.current_request:
			self.current_request.collect_incoming_data (data)
		else:
			self.in_buffer = self.in_buffer + data
				
	def found_terminator (self):
		if self.is_rejected:
			return
			
		if self.current_request:			
			self.current_request.found_terminator()
			if DEBUG:
				self.__history.append ("REQUEST DONE")
				self.__history = self.__history [-30:]
			
		else:
			header = self.in_buffer
			#print ("####### CLIENT => SKITAI ##########################")
			#print (header)
			#print ("------------------------------------------------")
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

			if DEBUG: 
				self.__history.append ("START REQUEST: %s/%s %s" % (command, version, uri))				
			
			header = utility.join_headers (lines[1:])
			r = http_request.http_request (self, request, command, uri, version, header)
			
			self.request_counter.inc()
			self.server.total_requests.inc()
			
			if command is None:
				r.response.error (400)
				return
			
			for h in self.server.handlers:
				if h.match (r):
					try:
						self.current_request = r
						h.handle_request (r)
												
					except:
						self.server.trace()
						try: r.response.error (500)
						except: pass
							
					return
					
			try: r.response.error (404)
			except: pass	
		      				
	def close (self):
		if self.closed:
			return
		
		if self.current_request is not None:
			self.closable_producers.append (self.current_request.collector)
			self.closable_producers.append (self.current_request.producer)
			# 1. close forcely or by error, make sure that channel is None
			# 2. by close_when_done ()
			self.current_request.channel = None
			self.current_request = None
		
		for closable in self.closable_partners:
			if closable and hasattr (closable, "channel"):
				closable.channel = None
			
		for closable in self.closable_producers + self.closable_partners:
			if closable and hasattr (closable, "close"):
				try:
					closable.close ()
				except:
					self.server.trace()
		
		self.closable_producers, self.closable_partners = [], []
		self.discard_buffers ()
		asynchat.async_chat.close (self)
		self.connected = False		
		self.closed = True
		self.log_info ("channel-%s closed" % self.channel_number, "info")
			
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
	SERVER_IDENT = skitai.NAME
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
			self.log_info ('shutting down web server: %s' % self.server_name)
			self.close ()		
	
	def close (self):
		asyncore.dispatcher.close (self)
		for h in self.handlers:
			if hasattr (h, "close"):
				h.close ()
					
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
			self.request_logger.log (message, "")
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

def configure (name, response, keep_alive):
	from . import https_server
	http_server.SERVER_IDENT = name
	https_server.https_server.SERVER_IDENT = name + " (SSL)"
	http_channel.response_timeout = https_server.https_channel.response_timeout = not response and 10 or response
	http_channel.keep_alive = https_server.https_channel.keep_alive = not keep_alive and 10 or keep_alive

		
if __name__ == "__main__":
	pass
	