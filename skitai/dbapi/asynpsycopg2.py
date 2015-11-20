#-------------------------------------------------------
# Asyn PostgresSQL Dispatcher
# Hans Roh (hansroh@gmail.com)
# 2015.6.9
#-------------------------------------------------------

import asyncore 
import re 
import time 
import sys 
import threading 
import psycopg2 
from psycopg2.extensions import POLL_OK, POLL_WRITE, POLL_READ 
from skitai.server.threads import trigger 
from skitai.server import rcache


_STATE_OK = (POLL_OK, POLL_WRITE, POLL_READ)


class AsynConnect (asyncore.dispatcher):
	zombie_timeout = 120	
		
	def __init__ (self, address, dbname, user, password, lock = None, logger = None):		
		self.address = address
		self.dbname = dbname
		self.user = user
		self.password = password		
		self.lock = lock
		
		self.logger = logger
		self.request_count = 0
		self.execute_count = 0
		self.event_time = time.time ()
		self._cv = threading.Condition ()
		self.active = 0		
		self.conn = None
		self.cur = None
		
		self.initialize ()
		
		asyncore.dispatcher.__init__ (self)
	
	def duplicate (self):
		return self.__class__ (self.address, self.dbname, self.user, self.password, self.lock, self.logger)
		
	def initialize (self):					
		self.callback = None
		self.has_result = False
		self.out_buffer = ""
		self.exception_str = ""
		self.exception_class = None
		
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 2:
			self.error (psycopg2.OperationalError, "was entered shutdown process")	
			self.handle_close ()		
		return 0
	
	def is_deletable (self, timeout):
		if time.time () - self.event_time > timeout:
			if not self.isactive ():
				self.abort ()
				return True
		return False
	
	def empty_cursor (self):
		if self.has_result:
			try:
				result = self.fetchall ()
			except psycopg2.ProgrammingError:
				pass
			self.has_result = False
		
	def release (self):
		if not self.connected:
			return
		self.empty_cursor () 
		self.close ()
	
	def check_state (self, state):
		if state not in (_STATE_OK):
			self.error (psycopg2.OperationalError, "psycopg2.poll() returned %s" % state)
			self.logger (self.exception_str, "error")
			self.handle_close ()
	
	def poll (self):		
		try:
			return self.socket.poll ()
		except:
			self.logger.trace ()
			return -1
		
	def writable (self):			
		return self.out_buffer or not self.connected
		
	def readable (self):
		return self.connected and not self.out_buffer
		
	def maintern (self):	
		if self.isactive () and time.time () - self.event_time > self.zombie_timeout:
			if not self.has_result:
				# really error, disconnect
				self.error (psycopg2.OperationalError, "zombie psycopg2, enter shutdown process")
				self.handle_close ()
				
			else:
				# Auto Release For,
				# case 1. doesn't be called wait() or fetchwait()
				# case 2. previously timeouted
				#print ">>>>>>maintern-release", self, self.connected	
				self.release ()
			
	def error (self, err_class, err_msg):
		self.exception_class, self.exception_str = err_class, err_msg				
		
	def del_channel (self, map=None):
		fd = self._fileno
		if map is None:
			map = self._map
		if fd in map:
			del map[fd]
	
	def reconnect (self):
		self.close_socket ()
		self.connect ()
					
	def close_socket (self):
		self.connected = False		
		self.del_channel ()
		
		if self.cur:
			self.empty_cursor ()
			try: self.cur.close ()
			except: pass			
		try: self.conn.close ()
		except: pass
			
		self.cur = None
		self.conn = None
	
	def close (self, force = False):
		if force or self.exception_class:
			self.close_socket ()
		else:
			self.del_channel ()		
			
		if self.callback:
			if self.has_result:
				self.callback (self.cur.description, self.exception_class, self.exception_str, self.fetchall ())
			else:
				self.callback (None, self.exception_class, self.exception_str, None)
			self.callback = None
			
		self.expt_class, self.expt_str = None, None		
		self.set_active (False)
	
	def abort (self):
		self.callback = None
		self.close_socket ()	
		self.set_active (False)
				
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
	
	def get_execute_count (self):	
		return self.execute_count
		
	def add_channel (self, map = None):
		self.event_time = time.time ()
		return asyncore.dispatcher.add_channel (self, map)
			
	def del_channel (self, map=None):
		fd = self._fileno
		if map is None:
			map = self._map
		if fd in map:
			del map[fd]			
	  	
	def connect (self, force = 0):
		self.event_time = time.time ()
		host, port = self.address
		
		sock = psycopg2.connect (
			dbname = self.dbname,
			user = self.user,
			password = self.password,
			host = host,
			port = port,
			async = 1
		)		
		self.set_socket (sock)
	
	def handle_expt_event (self):
		self.handle_expt ()
		
	def handle_connect_event (self):
		state = self.poll ()
		if state == POLL_OK:	
			self.handle_connect ()
			self.connected = True
		else:
			self.check_state (state)
	
	def handle_write_event (self):		
		if not self.connected:
			self.handle_connect_event ()
		else:	
			self.handle_write ()
	
	def handle_expt (self):
		self.error (psycopg2.OperationalError, "socket panic")
		self.handle_close ()
		
	def handle_connect (self):
		self.del_channel ()
		self.conn = self.socket
		self.cur = self.conn.cursor()		
		self.set_socket (self.cur.connection)
		
	def handle_read (self):
		state = self.poll ()
		if self.cur and state == POLL_OK:
			self.event_time = time.time ()
			self.has_result = True
			self.close ()
		else:
			self.check_state (state)
							
	def handle_write (self):
		state = self.poll ()
		if self.cur and state == POLL_OK:
			self.event_time = time.time ()
			self.cur.execute (self.out_buffer)
			self.out_buffer = ""
		else:
			self.check_state (state)

	def set_timeout (self, timeout):
		self.zombie_timeout = timeout

	def handle_timeout (self):
		self.error (psycopg2.OperationalError, "Operation Timeout")
		self.handle_close ()
	
	def handle_error (self):
		dummy, exception_class, exception_str, tbinfo = asyncore.compact_traceback()
		self.error (exception_class, exception_str)
		self.logger.trace ()
		self.handle_close ()
	
	def handle_close (self):
		self.close ()
				
	#-----------------------------------------------------
	# DB methods
	#-----------------------------------------------------	
	def fetchall (self):
		result = self.cur.fetchall ()		
		self.has_result = False
		return result
		
	def execute (self, sql, callback):
		self.initialize ()
		
		self.callback = callback		
		self.event_time = time.time ()
		self.execute_count += 1					
		self.out_buffer = sql
		
		if not self.connected:
			self.connect ()
			
		else:
			state = self.poll ()
			if state != POLL_OK:
				self.reconnect ()
			else:
				self.add_channel ()			
		trigger.wakeselect ()


