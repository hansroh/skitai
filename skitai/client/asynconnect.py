import asynchat
import asyncore
import re
import os
import socket
import time
import sys
import zlib
import ssl
from errno import ECONNRESET, ENOTCONN, ESHUTDOWN, ECONNABORTED, EWOULDBLOCK
import select
import threading
from . import adns
from warnings import warn

class SocketPanic (Exception): pass
class TimeOut (Exception): pass

def set_timeout (timeout):
	for each in (AsynConnect, AsynSSLConnect, AsynSSLProxyConnect):
		each.zombie_timeout = timeout
		

class AsynConnect (asynchat.async_chat):
	ac_in_buffer_size = 4096
	ac_out_buffer_size = 4096
	zombie_timeout = 120
	keep_alive = 300
		
	def __init__ (self, address, lock = None, logger = None):
		self.address = address
		self.lock = lock
		self.logger = logger
		
		self.request_count = 0
		self.event_time = time.time ()
		self._cv = threading.Condition ()		
		self.active = 0
		self.ready = None
		self.proxy = False
		self.affluent = None
		self.initialize ()
		asynchat.async_chat.__init__ (self)
	
	def set_proxy (self, flag = True):
		self.proxy = flag
	
	def is_proxy (self):
		return self.proxy
			
	def log (self, msg, logtype):
		if self.request is not None and hasattr (self.request, "log"):
			self.request.log (msg, logtype)
		elif self.logger:
			self.logger (msg, logtype)
		else:
			warn ("No logger")
			
	def trace (self):		
		if self.request is not None and hasattr (self.request, "trace"):
			self.request.trace ()
		elif self.logger:
			self.logger.trace ()
		else:
			warn ("No logger for traceback")
				
	def duplicate (self):
		return self.__class__ (self.address, self.lock, self.logger)
			
	def initialize (self):
		self.request = None
		self.received = False
		self.close_it = True
		self.errcode = 0
		self.errmsg = ""
		self.raised_ENOTCONN = 0
		self.request_buffer = b""
		
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 2:
			self.error (12, "Server Entered Shutdown Process")
			self.handle_close ()
		return 0
		
	def readable (self):
		if self.affluent is not None:
			return asynchat.async_chat.readable (self)	and self.affluent ()
		return asynchat.async_chat.readable (self)	
	
	def writable (self):
		if self.ready is not None:
			return asynchat.async_chat.writable (self) and self.ready ()
		return asynchat.async_chat.writable (self)	
        
	def maintern (self):
		if self.isactive () and time.time () - self.event_time > self.zombie_timeout:
			# do not user close_socket (), this func might be called in the thread, and currently in select.select()
			self.handle_close ()
	
	def is_deletable (self, timeout):
		if time.time () - self.event_time > timeout:
			if not self.isactive ():
				self.abort ()
				return True
		return False
	
	def is_channel_in_map (self, map = None):
		if map is None:
			map = self._map
		return self._fileno in map
					
	def del_channel (self, map=None):
		fd = self._fileno
		if map is None:
			map = self._map
		if fd in map:
			del map[fd]		
					
	def close_socket (self):
		self.connected = False
		self.accepting = False		
		self.del_channel ()
		self._fineno = None
		
		if self.socket:
			try:
				self.socket.close()
			except socket.error as why:
				if why.args[0] not in (ENOTCONN, EBADF):
					raise					

	def close (self, force = False):
		if force:
			self.close_it = True
		
		if self.request:
			self.request.done (self.errcode, self.errmsg)		
			
		if self.connected and self.close_it:
			self.close_socket ()
		else:	
			self.del_channel ()
		
		self.request = None
		self.set_active (False)
	
	def abort (self):
		self.close_socket ()
		self.request = None
		self.set_active (False)
			
	def error (self, code, msg):
		self.close_it = True
		self.errcode = code
		self.errmsg = msg		
		
	def set_active (self, flag, nolock = False):
		if flag:
			flag = time.time ()
		else:
			flag = 0
			
		if nolock or self.lock is None:
			self.active = flag
			return
			
		self.lock.acquire ()
		self.active = flag
		self.request_count += 1
		self.lock.release ()
	
	def get_active (self, nolock = False):
		if nolock or self.lock is None:
			return self.active
		self.lock.acquire ()
		active = self.active
		self.lock.release ()	
		return active
	
	def isactive (self):	
		return self.get_active () > 0
	
	def isconnected (self):	
		return self.connected
		
	def get_request_count (self):	
		return self.request_count
	
	def add_channel (self, map = None):		
		return asynchat.async_chat.add_channel (self, map)
			
	def create_socket (self, family, type):
		self.family_and_type = family, type
		sock = socket.socket (family, type)
		sock.setblocking (0)
		self.set_socket (sock)
	
	def connect_with_adns (self):
		if adns.query:
			adns.query (self.address [0], "A", callback = self.connect)
		else:
			self.connect ()
				
	def connect (self, force = 0):
		self.event_time = time.time ()
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		
		try:
			if not adns.query:				
				asynchat.async_chat.connect (self, self.address)
				
			else:	
				res = adns.get (self.address [0], "A")						
				if res:				
					ip = res [-1]["data"]
					if ip:
						asynchat.async_chat.connect (self, (ip, self.address [1]))																		
				else:
					self.error (15, "DNS Not Found")
					self.handle_close ()					
					
		except:	
			self.handle_error ()
	
	def recv (self, buffer_size):
		self.event_time = time.time ()
		try:
			data = self.socket.recv(buffer_size)			
			if not data:
				if self.reconnect (): # disconnected by server
					self.log ("Connection Closed in recv (), Try Reconnect...", "info")
					return b''
				self.handle_close ()
				return b''
			else:
				return data
		
		except socket.error as why:
			if why.errno in asyncore._DISCONNECTED:
				if os.name == "nt":
					# winsock sometimes raise ENOTCONN and sometimes recovered.
					if why.errno == asyncore.ENOTCONN:
						if self.raised_ENOTCONN <= 3:
							self.raised_ENOTCONN += 1
							return b''
					else:
						self.raised_ENOTCONN = 0
						
				if self.reconnect (): # disconnected by server
					self.log ("Connection Closed By _DISCONNECTED in recv (), Try Reconnect...", "info")
					return b''
				self.close_it = True
				self.handle_close ()
				return b''
			else:
				raise
	
	def send (self, data):
		self.event_time = time.time ()
		try:
			return self.socket.send (data)
						
		except socket.error as why:
			if why.errno == EWOULDBLOCK:
				return 0
				
			elif why.errno in asyncore._DISCONNECTED:				
				if os.name == "nt":
					# winsock sometimes raise ENOTCONN and sometimes recovered.
					if why.errno == asyncore.ENOTCONN:
						if self.raised_ENOTCONN <= 3:
							self.raised_ENOTCONN += 1
							return 0
					else:
						self.raised_ENOTCONN = 0
						
				if self.reconnect ():
					self.log ("Connection Closed in send (), Try Reconnect...", "info")
					return 0
				self.close_it = True				
				self.handle_close ()
				return 0
				
			else:
				raise
	
	def reconnect (self):	
		if self.received:
			return False
		return self.request.retry ()		

	def close_if_over_keep_live (self):
		if time.time () - self.event_time > self.keep_alive:			
			if self.connected:				
				self.close_socket ()
			return True
		return False
		
	def start_request (self, request):
		self.initialize ()
		self.request = request
		
		if self.connected:
			self.close_if_over_keep_live () # check keep-alive
		
		try:
			if not self.connected:
				self.connect ()
			else:
				# should keep order
				self.initiate_send ()
				self.add_channel ()				
			
		except:
			self.handle_error ()
	
	def initiate_send (self):
		if self.is_channel_in_map ():
			return asynchat.async_chat.initiate_send (self)
		
	# proxy POST need no init_send
	def push (self, thing, init_send = True):
		if type (thing) is bytes:
			asynchat.async_chat.push (self, thing)
		else:
			self.push_with_producer (thing, init_send)	
		
	def push_with_producer (self, producer, init_send = True):
		self.producer_fifo.append (producer)
		if init_send:
			self.initiate_send ()
					
	def collect_incoming_data (self, data):
		if not self.request:
			return # already closed
		self.received = True
		#print (repr (data[:79]))
		self.request.collect_incoming_data (data)
	
	def found_terminator (self):
		if not self.request: 
			return # already closed
		self.request.found_terminator ()
		
	def set_timeout (self, timeout):
		self.zombie_timeout = timeout
	
	def handle_connect (self):
		try: 
			self.request.when_connected ()
		except AttributeError:
			pass
			
	def handle_timeout (self):
		self.log ("socket timeout", "fail")
		self.error (13, "Socket Timeout")
		self.handle_close ()
		
	def handle_expt (self):
		self.loggger ("socket panic", "fail")
		self.error (14, "Socket Panic")
		self.handle_close ()
	
	def handle_error (self):
		self.trace ()
		self.error (11, "Exception")
		self.handle_close()
	
	def handle_expt_event(self):
		err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
		if err != 0:
			self.log ("SO_ERROR %d Occurred" % err, "warn")
			self.error (10, "Socket %d Error" % err)			
			self.handle_close ()
		else:
			self.handle_expt ()


class AsynSSLConnect (AsynConnect):	
	ac_in_buffer_size = 65535 # generally safe setting 65535 for SSL
	ac_out_buffer_size = 65535
	
	def connect (self, force = 0):
		self.handshaking = False
		self.handshaked = False
		AsynConnect.connect (self, force)
	
	def handshake (self):
		if not self.handshaking:
			err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
			if err != 0:
				raise socket.error(err, _strerror(err))	
			self.socket = ssl.wrap_socket (self.socket, do_handshake_on_connect = False)
			self.handshaking = True
			
		try:
			self.socket.do_handshake ()
		except ssl.SSLError as why:
			if why.args [0] in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):				
				return False
			raise ssl.SSLError(why)
		self.handshaked = True
		return True
							
	def handle_connect_event(self):
		if not self.handshaked and not self.handshake ():
			return	
		# handshaking done
		self.handle_connect()
		self.connected = True
		
	def recv (self, buffer_size):
		self.event_time = time.time ()
		try:
			data = self.socket.recv (buffer_size)
			
			if not data:
				if self.reconnect ():
					self.log ("SSL Connection Closed in recv (), Retry Connect...", "info")					
					return b''					
				self.handle_close ()
				return b''
			else:
				return data

		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_READ:
				return b'' # retry
			
			# closed connection
			elif why.errno == ssl.SSL_ERROR_ZERO_RETURN:
				if self.reconnect (): # disconnected by server
					self.log ("Connection Closed (SSL_ERROR_ZERO_RETURN) in recv (), Try Reconnect...", "info")
					return b''
				self.close_it = True
				self.handle_close ()
				return b''	
				
			# eof error
			elif why.errno == ssl.SSL_ERROR_EOF:
				self.log ("SSL_ERROR_EOF Error Occurred in recv ()", "warn")
				self.close_it = True
				self.handle_close ()
				return b''
				
			else:
				raise

	def send (self, data):
		self.event_time = time.time ()
		try:
			return self.socket.send (data)

		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_WRITE:
				return 0
			elif why.errno == ssl.SSL_ERROR_ZERO_RETURN:
				if self.reconnect ():
					self.log ("Connection Closed (SSL_ERROR_ZERO_RETURN) in send (), Try Reconnect...", "info")
					return 0
				self.close_it = True	
				self.handle_close ()
				return 0
			else:
				raise


class AsynSSLProxyConnect (AsynSSLConnect, AsynConnect):
	def __init__ (self, address, lock = None, logger = None):
		AsynConnect.__init__ (self, address, lock, logger)
		self.proxy_accepted = False
	
	def handle_connect_event (self):		
		AsynConnect.handle_connect_event (self)
	
	def recv (self, buffer_size):
		if self.handshaked or self.handshaking:
			return AsynSSLConnect.recv (self, buffer_size)				
		else:
			return AsynConnect.recv (self, buffer_size)
		
	def send (self, data):
		if not self.handshaked and self.proxy_accepted and self.connected:
			if not self.handshake ():
				return 0		
		if self.handshaked or self.handshaking:
			return AsynSSLConnect.send (self, data)
		else:
			return AsynConnect.send (self, data)
