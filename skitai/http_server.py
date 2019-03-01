#!/usr/bin/env python

import sys
import asyncore, asynchat
import re, socket, time, threading, os
from . import http_request, counter
from aquests.protocols.http import http_util, http_date
from aquests.athreads import threadlib
from skitai import lifetime
from rs4 import producers, compressors
from collections import deque
import signal
import ssl
import skitai
from hashlib import md5
from rs4.psutil.processutil import set_process_name
if os.name == "posix":
	import psutil
	CPUs = psutil.cpu_count()

PID = {}
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
	closed = False
	is_rejected = False
	
	keep_alive = 30
	network_timeout = 30
	zombie_timeout = 30
	
	fifo_class = deque
	
	def __init__ (self, server, conn, addr):
		self.channel_number = http_channel.channel_count.inc ()
		self.request_counter = counter.counter()
		self.bytes_out = counter.counter()
		self.bytes_in = counter.counter()
		
		#asynchat.async_chat.__init__ (self, conn)
		self.ac_in_buffer = b''
		self.incoming = []
		self.producer_fifo = self.fifo_class ()
		asyncore.dispatcher.__init__(self, conn)
		
		self.server = server
		self.addr = addr		
		self.set_terminator (b'\r\n\r\n')
		self.in_buffer = b''
		self.creation_time = int (time.time())
		self.event_time = int (time.time())
		self.__history = []
		self.__sendlock = None
		self.producers_attend_to = []
		self.things_die_with = []		
		
	def use_sendlock (self):
		self.__sendlock  = threading.Lock ()
		self.initiate_send = self._initiate_send_ts
			
	def get_history (self):
		return self.__history
			
	def reject (self):
		self.is_rejected = True		
	
	def _initiate_send_ts (self):
		lock = self.__sendlock
		lock.acquire ()
		try:
			asynchat.async_chat.initiate_send (self)		
			try: is_working = self.producer_fifo.working ()
			except AttributeError: 	is_working = len (self.producer_fifo)
		finally:	
			lock.release ()			
		if not is_working:
			self.done_request ()		
		
	def initiate_send (self):
		asynchat.async_chat.initiate_send (self)		
		try: is_working = self.producer_fifo.working ()
		except AttributeError: 	is_working = len (self.producer_fifo)
		if not is_working:
			self.done_request ()		
			
	def readable (self):		
		return not self.is_rejected and asynchat.async_chat.readable (self)
		
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
		self.close ()
	
	def set_timeout (self, timeout):
		self.zombie_timeout = timeout
	
	def set_socket_timeout (self, timeout):	
		self.keep_alive = timeout
		self.network_timeout = timeout
			
	def attend_to (self, thing):
		if not thing: return
		self.producers_attend_to.append (thing)
	
	def die_with (self, thing, tag):
		if not thing: return
		self.things_die_with.append ((thing, tag))
		
	def done_request (self):	
		self.producers_attend_to = [] # all producers are finished	
		self.set_timeout (self.keep_alive)		
							
	def send (self, data):
		#print	("SEND", repr (data), self.get_terminator ())
		self.event_time = int (time.time())
		result = asynchat.async_chat.send (self, data)		
		self.server.bytes_out.inc (result)
		self.bytes_out.inc (result)
		return result
	
	def recv (self, buffer_size):
		self.event_time = int (time.time())		
		try:
			result = asynchat.async_chat.recv (self, buffer_size)
			lr = len (result)
			self.server.bytes_in.inc (lr)
			self.bytes_in.inc (lr)
			if not result:
				self.handle_close ()
				return b""		
			#print	("RECV", repr(result), self.get_terminator ())
			return result
			
		except MemoryError:
			lifetime.shutdown (1, 1.0)
				
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
				command, uri, version = http_util.crack_request (request)
			except:
				self.log_info ("channel-%s invaild request header" % self.channel_number, "fail")
				return self.close ()

			if DEBUG: 
				self.__history.append ("START REQUEST: %s/%s %s" % (command, version, uri))				
			
			header = http_util.join_headers (lines[1:])
			r = http_request.http_request (self, request, command, uri, version, header)
			self.set_timeout (self.network_timeout)
			
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
	
	def handle_abort (self):
		self.close (ignore_die_partner = True)
		self.log_info ("channel-%s aborted" % self.channel_number, "info")
			      				
	def close (self, ignore_die_partner = False):
		if self.closed:
			return
		
		for closable, tag in self.things_die_with:
			if closable and hasattr (closable, "channel"):
				closable.channel = None
			self.journal (tag)
			if not ignore_die_partner:
				self.producers_attend_to.append (closable)
				
		if self.current_request is not None:
			self.producers_attend_to.append (self.current_request.collector)
			self.producers_attend_to.append (self.current_request.producer)
			# 1. close forcely or by error, make sure that channel is None
			# 2. by close_when_done ()
			self.current_request.channel = None
			self.current_request = None
			
		for closable in self.producers_attend_to:
			if closable and hasattr (closable, "close"):
				try:
					closable.close ()
				except:
					self.server.trace()
		
		self.producers_attend_to, self.things_die_with = [], []
		self.discard_buffers ()
		asynchat.async_chat.close (self)
		self.connected = False		
		self.closed = True
		self.log_info ("channel-%s closed" % self.channel_number, "info")
	
	def journal (self, reporter):
		self.log (
			"%s closed, client %s:%s, bytes in: %s, bytes out: %s for %d seconds " % (
				reporter,
				self.addr [0], 
				self.addr [1], 
				self.bytes_in,
				self.bytes_out,
				time.time () - self.creation_time
			)
		)
					
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
	
	maintern_interval = 0
	critical_point_cpu_overload = 90.0
	critical_point_continuous = 3
	
	def __init__ (self, ip, port, server_logger = None, request_logger = None):
		global PID
		
		self.handlers = []
		self.ip = ip
		self.port = port
		asyncore.dispatcher.__init__ (self)

		if ip.find (":") != -1:
			self.create_socket (socket.AF_INET6, socket.SOCK_STREAM)		
		else:			
			self.create_socket (socket.AF_INET, socket.SOCK_STREAM)		

		self.set_reuse_addr ()
		try:
			self.bind ((ip, port))
		except OSError as why:			
			if why.errno == 98:
				server_logger ("address already in use, cannot start server", "fatal")
			else:
				server_logger.trace ()	
			sys.exit (0)
		
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
		self.shutdown_phase = 2		
		
		self.__last_maintern = time.time ()
				
		host, port = self.socket.getsockname()
		hostname = socket.gethostname()
		try:			
			self.server_name = socket.gethostbyaddr (hostname)[0]
		except socket.error:			
			self.server_name = hostname
		self.hash_id = md5 (self.server_name.encode ('utf8')).hexdigest() [:4]		
		self.server_port = port
		
	def _serve (self, shutdown_phase = 2):
		self.shutdown_phase = shutdown_phase
		self.listen (os.name == "posix" and 4096 or 256)
	
	def serve (self, sub_server = None): 
		if sub_server:
			sub_server._serve (max (1, self.shutdown_phase - 1))
		self._serve ()			
		
	def fork (self, numworker = 1):
		global ACTIVE_WORKERS, SURVAIL, PID, EXITCODE
		
		if os.name == "nt":
			set_process_name (skitai.get_proc_title ())
			signal.signal(signal.SIGTERM, hTERMWORKER)			
		
		else:			
			while SURVAIL:
				try:	
					if ACTIVE_WORKERS < numworker:						
						pid = os.fork ()
						if pid == 0:							
							self.worker_ident = "worker #%d" % len (PID)
							set_process_name ("%s: %s" % (skitai.get_proc_title (), self.worker_ident))
							PID = {}
							signal.signal(signal.SIGTERM, hTERMWORKER)
							signal.signal(signal.SIGQUIT, hQUITWORKER)
							break
							
						else:
							set_process_name ("%s: master" % skitai.get_proc_title ())
							if not PID:								
								signal.signal(signal.SIGHUP, hHUPMASTER)
								signal.signal(signal.SIGTERM, hTERMMASTER)
								signal.signal(signal.SIGINT, hTERMMASTER)
								signal.signal(signal.SIGQUIT, hQUITMASTER)
								signal.signal (signal.SIGCHLD, hCHLD)
							
							ps = psutil.Process (pid)
							ps.x_overloads = 0
							PID [pid] = ps
							ACTIVE_WORKERS += 1
							#print ('-----', PID, ACTIVE_WORKERS)
					
					now = time.time ()
					if self.maintern_interval and now - self.__last_maintern > self.maintern_interval:						
						self.maintern (now)		
					time.sleep (1)
					
				except KeyboardInterrupt:
					EXITCODE = 0
					DO_SHUTDOWN (signal.SIGTERM)
					break
			
			if self.worker_ident == "master":
				return EXITCODE
				
		self.log_info ('%s (%s) started on %s:%d' % (
			self.SERVER_IDENT, self.worker_ident, self.server_name, self.port)
		)
	
	usages = []
	cpu_stat = []
	def maintern (self, now):
		global PID, CPUs
		
		self.__last_maintern = now
		usages = []
		for ps in PID.values ():
			if ps is None:
				continue
							
			try:
				usage = ps.cpu_percent ()
			except (psutil.NoSuchProcess, AttributeError):
				# process changed, maybe next time
				usage = 0.0
			usages.append ((ps, usage))
		
		self.usages.append (sum ([x [1] for x in usages]) / len (usages))
		self.usages = self.usages [-45:]
		
		self.cpu_stat = []
		max_usage = 0
		for c in (3, 15, 45):
			# 1m, 5m, 15
			array = self.usages [-c:]
			self.cpu_stat.append ((max (array), int (sum (array) / c)))					
		
		if self.cpu_stat [0][0] > 10:
			# 60% for 1m
			self.log ("CPU percent: " + ", ".join (["%d/%d" % unit for unit in self.cpu_stat]))
			
		for ps, usage in usages:						
			if usage < self.critical_point_cpu_overload:
				ps.x_overloads = 0 #reset count
				continue
							
			ps.x_overloads += 1	
			if ps.x_overloads > self.critical_point_continuous:				
				self.log ("process %d is overloading, try to kill..." % ps.pid, 'fatal')
				sig = ps.x_overloads > (self.critical_point_continuous + 2) and signal.SIGKILL or signal.SIGTERM
				try:
					os.kill (ps.pid, sig)
				except OSError:
					pass
			
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
		if phase == self.shutdown_phase:
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
		#print ('-----', self.worker_ident)
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
	
	def status (self):
		global PID
		
		return 	{
			"child_pids": list (PID.keys ()),
			"ident": "%s for %s" % (self.worker_ident, self.SERVER_IDENT),
			'server_name': self.server_name,	
			"start_time": self.start_time, 		
			'hash_id': self.hash_id,	
			"port": self.port,
			"total_clients": self.total_clients.as_long(),
			"total_request": self.total_requests.as_long(), 
			"total_exceptions": self.exceptions.as_long(), 
			"bytes_out": self.bytes_out.as_long(), 
			"bytes_in": self.bytes_in.as_long(),
			"cpu_percent":	self.cpu_stat
		}
			
def hCHLD (signum, frame):
	global ACTIVE_WORKERS, PID
	
	ACTIVE_WORKERS -= 1
	try:
		pid, status = os.waitpid (0, 0)
	except ChildProcessError:
		pass
	else:
		PID [pid]	= None

def hTERMWORKER (signum, frame):			
	lifetime.shutdown (0, 1.0)

def hQUITWORKER (signum, frame):			
	lifetime.shutdown (0, 30.0)
	
def DO_SHUTDOWN (sig):
	global PID
	
	signal.signal (signal.SIGCHLD, signal.SIG_IGN)
	for pid in PID:
		if PID [pid] is None:
			continue			
		try: os.kill (pid, sig)
		except OSError: pass
			
def hTERMMASTER (signum, frame):
	global EXITCODE, SURVAIL
	SURVAIL = False
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

def configure (name, network_timeout = 0, keep_alive = 0):
	from . import https_server
	http_server.SERVER_IDENT = name
	https_server.https_server.SERVER_IDENT = name + " (SSL)"
	http_channel.keep_alive = https_server.https_channel.keep_alive = not keep_alive and 2 or keep_alive
	http_channel.network_timeout = https_server.https_channel.network_timeout = not network_timeout and 30 or network_timeout
	
		
if __name__ == "__main__":
	pass
	