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

DEBUG = False

class SocketPanic (Exception): pass
class TimeOut (Exception): pass

class AsynConnect (asynchat.async_chat):
	ac_in_buffer_size = 65535
	ac_out_buffer_size = 65535
	zombie_timeout = 10
	keep_alive_timeout = 10
	network_delay_timeout = 10	
	ready = None
	affluent = None	
	
	request_count = 0
	active = 0
	proxy = False
			
	def __init__ (self, address, lock = None, logger = None):
		self.address = address
		self.lock = lock
		self.logger = logger
		self._cv = threading.Condition ()		
		self.set_event_time ()
		self.proxy = False
		self.handler = None
		self.__history = []
		self.initialize_connection ()
		asynchat.async_chat.__init__ (self)
	
	def get_history (self):
		return self.__history
		
	def initialize_connection (self):		
		self._raised_ENOTCONN = 0 # for win32
		self._handshaking = False
		self._handshaked = False		
		
		self.established = False		
		self.upgraded = False		
		self.ready = None
		self.affluent = None		
			
	def set_event_time (self):
		self.event_time = time.time ()
		
	def set_proxy (self, flag = True):
		self.proxy = flag
	
	def is_proxy (self):
		return self.proxy
			
	def log (self, msg, logtype):
		if self.handler is not None and hasattr (self.handler, "log"):
			self.handler.log (msg, logtype)
		elif self.logger:
			self.logger (msg, logtype)
		else:
			warn ("No logger")
			
	def trace (self):		
		if self.handler is not None and hasattr (self.handler, "trace"):
			self.handler.trace ()
		elif self.logger:
			self.logger.trace ()
		else:
			warn ("No logger for traceback")
				
	def duplicate (self):
		return self.__class__ (self.address, self.lock, self.logger)
		
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 2:
			self.handle_close (705, "Server Entered Shutdown Process")
		
	def readable (self):
		if self.affluent is not None:
			return asynchat.async_chat.readable (self)	and self.affluent ()
		return asynchat.async_chat.readable (self)	
	
	def writable (self):
		if self.ready is not None:
			return asynchat.async_chat.writable (self) and self.ready ()
		return asynchat.async_chat.writable (self)	
        
	def maintern (self, object_timeout):
		# check inconsistency, maybe impossible
		a, b = self.handler and 1 or 0, self.isactive () and 1 or 0
		if a != b:
			self.disconnect ()
			self.end_tran ()
					
		if time.time () - self.event_time > object_timeout:
			if not self.isactive ():	
				self.disconnect ()
				return True
		
		return False
	
	def is_channel_in_map (self, map = None):
		if map is None:
			map = self._map
		return self._fileno in map
		
	def set_active (self, flag, nolock = False):
		if DEBUG: self.__history.append ("SET ACTIVE %s" % flag) 
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
		if DEBUG: self.__history.append ("CHANNEL ADDED") 
		self.zombie_timeout =  self.network_delay_timeout		
		self._fileno = self.socket.fileno ()
		return asynchat.async_chat.add_channel (self, map)
		
	def del_channel (self, map = None):
		if DEBUG: self.__history.append ("CHANNEL REMOVED") 
		asynchat.async_chat.del_channel (self, map)
		# make default and sometimes reset server'stimeout	
		self.zombie_timeout =  self.keep_alive_timeout
				
	def create_socket (self, family, type):
		self.family_and_type = family, type
		sock = socket.socket (family, type)
		sock.setblocking (0)
		self.set_socket (sock)
	
	def connect (self):
		if adns.query:
			if DEBUG: self.__history.append ("QUERYING DNS")
			adns.query (self.address [0], "A", callback = self.continue_connect)
		else:
			# no adns query
			self.continue_connect (True)
		
	def continue_connect (self, answer = None):
		if not answer:
			if DEBUG: self.__history.append ("DNS FAILED")
			self.log ("DNS not found - %s" % self.address [0], "error")
			return self.handle_close (704, "DNS Not Found")
		
		if DEBUG: self.__history.append ("CREATING SOCKET & CONNECTING...") 
		self.initialize_connection ()
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
					self.handle_close (704, "DNS Not Found")
					
		except:	
			self.handle_error ()
	
	def recv (self, buffer_size):		
		self.set_event_time ()
		try:
			data = self.socket.recv(buffer_size)	
			#print ("+++++DATA", len (data), repr (data [:40]))				
			if not data:
				self.handle_close (700, "Connection closed unexpectedly in recv")
				return b''
			else:
				return data		
		except socket.error as why:
			if why.errno in asyncore._DISCONNECTED:				
				self.handle_close (700, "Connection closed unexpectedly in recv")
				return b''				
			else:
				raise
	
	def send (self, data):		
		self.set_event_time ()
		try:
			return self.socket.send (data)
		except socket.error as why:
			if why.errno == EWOULDBLOCK:
				return 0				
			elif why.errno in asyncore._DISCONNECTED:
				#print (">>>>>>>>>> why.errno == asyncore.ENOTCONN", why.errno == asyncore.ENOTCONN)
				if os.name == "nt" and why.errno == asyncore.ENOTCONN:
					# winsock sometimes raise ENOTCONN and sometimes recovered.
					# Found this error at http://file.hungryboarder.com:8080/HBAdManager/pa.html?siteId=hboarder&zoneId=S-2
					if self._raised_ENOTCONN <= 3:
						self._raised_ENOTCONN += 1
						return 0
					else:
						self._raised_ENOTCONN = 0
				self.handle_close (700, "Connection closed unexpectedly in send")
				return 0
			else:
				raise
	
	def close_if_over_keep_live (self):
		if time.time () - self.event_time > self.zombie_timeout:
			if DEBUG: self.__history.append ("KEEP-ALIVE TIMEOUT") 
			self.disconnect ()
	
	def initiate_send (self):
		if self.is_channel_in_map ():
			return asynchat.async_chat.initiate_send (self)
	
	def set_zombie_timeout (self, timeout = 10):
		self.zombie_timeout = timeout
	
	def set_zombie_timeout_by_case (self):
		if self.affluent or self.ready:
			self.zombie_timeout = self.network_delay_timeout * 2
		else:	
			self.zombie_timeout = self.network_delay_timeout
	
	def set_network_delay_timeout (self, timeout = 10):
		self.network_delay_timeout = timeout
	
	def set_keep_alive_timeout (self, timeout = 10):
		self.keep_alive_timeout = timeout
		
	def handle_connect (self):
		if DEBUG: self.__history.append ("CONNECTED") 
		try: 
			self.handler.has_been_connected ()
		except AttributeError:
			pass
		
	def handle_read (self):
		self.set_zombie_timeout_by_case ()		
		asynchat.async_chat.handle_read (self)
		
	def handle_write (self):
		self.set_zombie_timeout_by_case ()		
		asynchat.async_chat.handle_write (self)
			
	def handle_expt (self):
		self.logger ("socket panic", "fail")
		self.handle_close (703, "Socket Panic")
	
	def handle_error (self):
		self.trace ()
		self.handle_close(701, "Exception")
	
	def handle_timeout (self):
		self.log ("socket timeout", "fail")
		self.handle_close (702, "Socket Timeout")
		
	def handle_expt_event(self):
		err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
		if err != 0:
			self.log ("Socket Error %d Occurred" % err, "warn")
			self.handle_close (706, "Socket %d Error" % err)
		else:
			self.handle_expt ()
	
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
	
	def handle_close (self, code = 700, msg = "Disconnected by Server"):		
		if DEBUG: self.__history.append ("HANDLE_CLOSE %d %s" % (code, msg)) 
		self.errcode = code
		self.errmsg = msg
		self.close ()
							
	def collect_incoming_data (self, data):
		if not self.handler:
			self.logger ("recv data but no hander, droping data %d" % len (data), "warn")
			self.disconnect ()
			return
		self.handler.collect_incoming_data (data)
	
	def found_terminator (self):
		if not self.handler:
			self.logger ("found terminator but no handler", "warn")
			self.disconnect ()
			return # already closed
		self.handler.found_terminator ()
	
	def disconnect (self):
		# no error
		if DEBUG: self.__history.append ("DISCONNECTING") 
		self.handle_close (0, "")
	
	def reconnect (self):
		if DEBUG: self.__history.append ("RECONNECTING")
		self.disconnect ()
		self.connect ()
		
	def close (self):
		if self.socket:
			# self.socket is still None, when DNS not found
			asynchat.async_chat.close (self)
		
			# re-init asychat
			self.ac_in_buffer = b''
			self.incoming = []
			self.producer_fifo.clear()
			if DEBUG: self.__history.append ("DISCONNECTED")
		else:
			if DEBUG: self.__history.append ("CAN'T CLOSE, NOT CONNECTED")
		
		if self.handler is None:
			if DEBUG: self.__history.append ("NO HANDLER, GOTO END TRAN")
			self.end_tran () # automatic end_tran when timeout occured by maintern
		elif self.errcode:
			if DEBUG: self.__history.append ("CALL CONNECTION CLOSED")
			self.handler.connection_closed (self.errcode, self.errmsg)
			
	def end_tran (self):
		self.del_channel ()
		self.handler = None
		self.set_active (False)		
		if DEBUG: 
			self.__history.append ("END TRAN")
			self.__history = self.__history [-30:]
			
	def begin_tran (self, handler):
		self.errcode = 0
		self.errmsg = ""
			
		self.handler = handler		
		self.set_event_time ()
		if DEBUG: self.__history.append ("BEGIN TRAN %s %s" % (handler.method, handler.request.uri))
		
		if self.connected:
			self.close_if_over_keep_live () # check keep-alive
						
		try:
			if self.connected:
				# should keep order
				self.initiate_send ()
				self.add_channel ()
			else:
				self.connect ()
		except:
			self.handle_error ()
	
	
class AsynSSLConnect (AsynConnect):	
	ac_out_buffer_size = 65536
	ac_in_buffer_size = 65536
		
	def handshake (self):
		if not self._handshaking:
			err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
			if err != 0:
				raise socket.error(err, _strerror(err))	
			self.socket = ssl.wrap_socket (self.socket, do_handshake_on_connect = False)
			self._handshaking = True
			
		try:
			self.socket.do_handshake ()
		except ssl.SSLError as why:
			if why.args [0] in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):				
				return False
			raise ssl.SSLError(why)
		self._handshaked = True		
		return True
							
	def handle_connect_event (self):	
		if not self._handshaked and not self.handshake ():
			return
		# handshaking done
		self.handle_connect()
		self.connected = True
		
	def recv (self, buffer_size):
		self.set_event_time ()
		try:
			data = self.socket.recv (buffer_size)			
			if not data:				
				self.handle_close (700, "Connection closed unexpectedly")
				return b''
			else:				
				return data

		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_READ:
				return b'' # retry			
			# closed connection
			elif why.errno in (ssl.SSL_ERROR_ZERO_RETURN, ssl.SSL_ERROR_EOF):
				self.handle_close (700, "Connection closed by SSL_ERROR_ZERO_RETURN or SSL_ERROR_EOF")
				return b''
				
			else:
				raise

	def send (self, data):
		self.set_event_time ()
		try:
			return self.socket.send (data)			

		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_WRITE:
				return 0
			elif why.errno == ssl.SSL_ERROR_ZERO_RETURN:				
				self.handle_close (700, "Connection blosed by SSL_ERROR_ZERO_RETURN")
				return 0
			else:
				raise


class AsynSSLProxyConnect (AsynSSLConnect, AsynConnect):
	ac_out_buffer_size = 65536
	ac_in_buffer_size = 65536
	
	def handle_connect_event (self):
		if self.established:
			AsynSSLConnect.handle_connect_event (self)
		else:	
			AsynConnect.handle_connect_event (self)
	
	def recv (self, buffer_size):		
		if self._handshaked or self._handshaking:
			return AsynSSLConnect.recv (self, buffer_size)				
		else:
			return AsynConnect.recv (self, buffer_size)
			
	def send (self, data):		
		if self._handshaked or self._handshaking:
			return AsynSSLConnect.send (self, data)
		else:
			return AsynConnect.send (self, data)
