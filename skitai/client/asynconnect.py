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

class AsynConnect (asynchat.async_chat):
	ac_in_buffer_size = 4096
	ac_out_buffer_size = 4096
	zombie_timeout = 10
	keep_alive_timeout = 10
	network_delay_timeout = 10	
	ready = None
	affluent = None	
	
	request_count = 0
	active = 0
	proxy = False		
	debug_info = None
			
	def __init__ (self, address, lock = None, logger = None):
		self.address = address
		self.lock = lock
		self.logger = logger
		self.event_time = time.time ()
		self._cv = threading.Condition ()		
		
		self._handshaking = False # SSL handsjking
		self._handshaked = False # SSL handsjking
		
		self.established = False # used for tunneling
		self.upgraded = False # used for web socket
		
		asynchat.async_chat.__init__ (self)
		self.initialize ()
	
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
	
	def handle_close (self):
		self.producer_fifo.clear ()
		asynchat.async_chat.handle_close (self)
				
	def initialize (self):
		self.event_time = time.time ()
		self.handler = None
		self.sent = 0
		self.received = 0
		self.close_it = False
		self.errcode = 0
		self.errmsg = ""
		self.raised_ENOTCONN = 0
		self.request_buffer = b""
		
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 2:
			self.error (705, "Server Entered Shutdown Process")
			self.handle_close ()
		
	def readable (self):
		if self.affluent is not None:
			return asynchat.async_chat.readable (self)	and self.affluent ()
		return asynchat.async_chat.readable (self)	
	
	def writable (self):
		if self.ready is not None:
			return asynchat.async_chat.writable (self) and self.ready ()
		return asynchat.async_chat.writable (self)	
        
	def maintern (self):
		# if self.is_channel_in_map (), mainterned by lifetime
		if not self.is_channel_in_map () and self.isactive () and time.time () - self.event_time > self.zombie_timeout:			# do not user close_socket (), this func might be called in the thread, and currently in select.select()
			self.close (True)
	
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
	
	def cancel_request (self):
		self.producer_fifo.clear()	
	
	def create_new_socket (self):
		self.close_socket ()
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
						
	def close_socket (self):
		self.connected = False
		self.accepting = False
		
		self._handshaking = False
		self._handshaked = False
		self.established = False
		self.upgraded = False
		
		self.del_channel ()
		self._fineno = None
		
		if self.socket:
			try:
				self.socket.close()
			except socket.error as why:
				if why.args[0] not in (ENOTCONN, EBADF):
					raise	
		
	def close (self, force = False):
		#print ("+++++++++++++++++++++++++++", time.time () - self.event_time, self.connected, self.sent, self.received)
		if force:
			self.close_it = True
		
		self.ready = None
		self.affluent = None		
		
		if self.connected and self.close_it:
			self.close_socket ()
		else:			
			self.del_channel ()
		
		if self.handler:
			ret = None
			try:			
				# request continue cause of 401 error
				ret = self.handler.case_closed (self.errcode, self.errmsg)					
			except:
				self.trace ()
			else:
				if ret is not None:
					return			
		
		self.handler = None
		self.set_active (False)
	
	def abort (self):
		try:
			self.close_socket ()
		finally:	
			self.handler = None
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
		self.zombie_timeout =  self.network_delay_timeout		
		return asynchat.async_chat.add_channel (self, map)
		
	def del_channel (self, map=None):
		fd = self._fileno
		if map is None:
			map = self._map
		if fd in map:
			del map[fd]		
		# make default and sometimes reset server'stimeout	
		self.zombie_timeout =  self.keep_alive_timeout
				
	def create_socket (self, family, type):
		self.family_and_type = family, type
		sock = socket.socket (family, type)
		sock.setblocking (0)
		self.set_socket (sock)
	
	def connect (self):
		if adns.query:
			adns.query (self.address [0], "A", callback = self.continue_connect)
		else:
			# no adns query
			self.continue_connect (True)
	
	def continue_connect (self, answer = None):
		if not answer:
			self.log ("DNS not found - %s" % self.asyncon.address [0], "error")
			self.error (704, "DNS Not Found")
			self.handle_close ()
			return
		
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
					self.error (704, "DNS Not Found")
					self.handle_close ()					
					
		except:	
			self.handle_error ()
	
	def recv (self, buffer_size):		
		self.event_time = time.time ()
		try:
			data = self.socket.recv(buffer_size)	
			#print ("+++++DATA", len (data), repr (data [:40]))				
			if not data:
				if not self.connected:
					return b''	
				if self.disconnect_handled (): # disconnected by server
					self.log ("Connection Closed in recv (), Try Reconnect...", "info")					
					return b''
				self.handle_close ()
				return b''
			else:
				self.received += len (data)
				return data
		
		except socket.error as why:
			if why.errno in asyncore._DISCONNECTED:
				if not self.received and why.errno == asyncore.ENOTCONN and os.name == "nt":
					# winsock sometimes raise ENOTCONN and sometimes recovered.					
					if self.raised_ENOTCONN <= 3:
						self.raised_ENOTCONN += 1
						return b''
					else:	
						self.raised_ENOTCONN = 0
					
				if self.disconnect_handled (): # disconnected by server
					self.log ("Connection Closed By _DISCONNECTED in recv (), Try Reconnect...", "info")
					return b''

				self.close_it = True
				self.handle_close ()
				return b''
			else:
				raise
	
	def send (self, data):
		#print ("+++++DATA", len (data), repr (data [:40]))	
		self.event_time = time.time ()
		try:
			sent = self.socket.send (data)
			self.sent += sent
			return sent
						
		except socket.error as why:
			if why.errno == EWOULDBLOCK:
				return 0
				
			elif why.errno in asyncore._DISCONNECTED:
				if not self.sent and why.errno == asyncore.ENOTCONN and os.name == "nt":
					# winsock sometimes raise ENOTCONN and sometimes recovered.
					if self.raised_ENOTCONN <= 3:
						self.raised_ENOTCONN += 1
						return 0
					else:
						self.raised_ENOTCONN = 0
						
				if self.disconnect_handled ():
					self.log ("Connection Closed in send (), Try Reconnect...", "info")
					return 0
					
				self.close_it = True				
				self.handle_close ()
				return 0
				
			else:
				raise
	
	def disconnect_handled (self):
		# server returned null byte
		# raised asyncore._DISCONNECTED
		# raised ssl.SSL_ERROR_ZERO_RETURN
		return self.handler.handle_disconnected ()		

	def close_if_over_keep_live (self):
		if time.time () - self.event_time > self.zombie_timeout:
			if self.connected:				
				self.close_socket ()
			return True
		return False
		
	def start_request (self, handler):
		self.initialize ()
		self.handler = handler
		self.debug_info = (handler.method, handler.uri, handler.http_version)
		
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
		if not self.handler:
			return # already closed				
		#print (repr (data[:79]))
		self.handler.collect_incoming_data (data)
	
	def found_terminator (self):
		if not self.handler: 
			return # already closed
		self.handler.found_terminator ()
	
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
		try: 
			self.handler.has_been_connected ()
		except AttributeError:
			pass
			
	def handle_timeout (self):
		#print ("*************************", self.zombie_timeout, time.time () - self.event_time, self.connected, self.sent, self.received)
		self.log ("socket timeout", "fail")
		self.error (702, "Socket Timeout")
		self.handle_close ()
		
	def handle_read (self):
		self.set_zombie_timeout_by_case ()
		asynchat.async_chat.handle_read (self)
		
	def handle_write (self):
		self.set_zombie_timeout_by_case ()
		asynchat.async_chat.handle_write (self)
			
	def handle_expt (self):
		self.loggger ("socket panic", "fail")
		self.error (703, "Socket Panic")
		self.handle_close ()
	
	def handle_error (self):
		self.trace ()
		self.error (701, "Exception")
		self.handle_close()
	
	def handle_expt_event(self):
		err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
		if err != 0:
			self.log ("SO_ERROR %d Occurred" % err, "warn")
			self.error (700, "Socket %d Error" % err)			
			self.handle_close ()
		else:
			self.handle_expt ()


class AsynSSLConnect (AsynConnect):	
	ac_in_buffer_size = 65535 # generally safe setting 65535 for SSL
	ac_out_buffer_size = 65535
	
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
		self.event_time = time.time ()
		try:
			data = self.socket.recv (buffer_size)			
			if not data:				
				if not self.connected:
					return b''
				if self.disconnect_handled ():
					self.log ("SSL Connection Closed in recv (), Retry Connect...", "info")					
					return b''					
				self.handle_close ()
				return b''
			else:				
				self.received += len (data)
				return data

		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_READ:
				return b'' # retry
			
			# closed connection
			elif why.errno == ssl.SSL_ERROR_ZERO_RETURN:
				if self.disconnect_handled (): # disconnected by server
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
			sent = self.socket.send (data)
			self.sent += sent

		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_WRITE:
				return 0
			elif why.errno == ssl.SSL_ERROR_ZERO_RETURN:
				if self.disconnect_handled ():
					self.log ("Connection Closed (SSL_ERROR_ZERO_RETURN) in send (), Try Reconnect...", "info")
					return 0
				self.close_it = True	
				self.handle_close ()
				return 0
			else:
				raise


class AsynSSLProxyConnect (AsynSSLConnect, AsynConnect):
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
