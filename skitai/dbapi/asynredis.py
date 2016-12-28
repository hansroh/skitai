from redis import connection as redisconn
import asynchat
from . import dbconnect	
import socket

DEBUG = True
LINE_FEED = b"\r\n"

import redis.connection


class PythonParser (redisconn.PythonParser):
	def __init__(self, buf):
		self._buffer = buf		
	
	
class AsynConnect (dbconnect.DBConnect, asynchat.async_chat):	
	def __init__ (self, address, params = None, lock = None, logger = None):
		dbconnect.DBConnect.__init__ (self, address, params, lock, logger)
		self.dbname, self.user, self.password = self.params
		self.redisconn = redisconn.Connection ()
		asynchat.async_chat.__init__ (self)
	
	def close (self):
		asynchat.async_chat.close (self)
	
	def end_tran (self):
		dbconnect.DBConnect.end_tran (self)
		asynchat.async_chat.del_channel (self)
								
	def close_case (self):
		if self.callback:
			self.callback ([("value",)], self.exception_class, self.exception_str, self.fetchall ())
			self.callback = None
		self.set_active (False)
	
	def add_channel (self, map = None):		
		self._fileno = self.socket.fileno ()
		return asynchat.async_chat.add_channel (self, map)		
			
	def handle_connect (self):
		self.set_event_time ()
		if self.user:			
			self.send_command ('AUTH', self.password)		
	
	def send_command (self, *args):
		self.set_event_time ()
		self.last_command = args [0]
		command = self.redisconn.pack_command (*args)
		if isinstance(command, list):
			command = b"".join (command)
		self.push (command)
		    						
	def connect (self):
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)		
		try:
			asynchat.async_chat.connect (self, self.address)
		except:	
			self.handle_error ()
	
	def collect_incoming_data (self, data):
		self.set_event_time ()
		self.data.append (data)
	
	def fetchall (self):
		res = self.response [0][0]
		self.response = []
		self.has_result = False
		return [(res,)]
	
	def add_element (self, e):
		if type (e) is bytes:
			e = e.decode ("utf8")
		self.response [-1].append (e)
		self.num_elements [-1] -= 1
		while self.num_elements and self.num_elements [-1] <= 0:		
			self.num_elements.pop (-1)
			if len (self.response) > 1:
				item = self.response.pop (-1)
				self.response [-1].append (item)				
	
	def found_terminator (self):
		if self.last_command == "AUTH":
			assert self.data [-1] != "+OK", "AUTH Failed"
			if self.dbname:
				return self.send_command ('SELECT', self.dbname)
										
		if self.last_command == "SELECT":
			assert self.data [-1] != "+OK", "No Database"
			return

		header = self.data [-1][:1]
		if self.length != -1:
			self.add_element (self.data [-1][:-2])
			self.data = []
			self.length = -1
			self.set_terminator (LINE_FEED)
			
		elif header in b"+-":
			self.add_element (self.data [-1][1:])
			self.has_result = True	
			self.set_terminator (LINE_FEED)
			
		elif header in b":":
			self.add_element ((int (self.data [-1][1:]),))			
			self.set_terminator (LINE_FEED)
			
		elif header == b"$":
			self.length = int (self.data [-1][1:]) + 2
			if self.length == -1:
				self.add_element (None)
				self.data = []				
				self.set_terminator (LINE_FEED)	
			else:	
				self.set_terminator (self.length)
		
		elif header == b"*":			
			num_elements = int (self.data [-1][1:])			
			if self.num_elements [-1] == -1:
				self.add_element (None)
			else:
				self.response.append ([])
				self.num_elements.append (num_elements)
			self.data = []
			self.set_terminator (LINE_FEED)
			
		else:
			raise ValueError ("Protocol Error")	
		
		if not self.num_elements:
			self.has_result = True
			self.close_case_with_end_tran ()
	
	def begin_tran (self, callback, sql):			
		dbconnect.DBConnect.begin_tran (self, callback, sql)
		self.response = [[]]
		self.data = []
		self.length = -1
		self.num_elements = [0]
		self.last_command = None		
		self.set_terminator (LINE_FEED)
						
	def execute (self, callback, *command):
		self.begin_tran (callback, command)		
		if not self.connected:
			self.connect ()
		else:
			# keep this order
			self.initiate_send ()
			self.add_channel ()			
		self.send_command (*command)
		