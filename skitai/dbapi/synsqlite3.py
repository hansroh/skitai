import sqlite3
from . import dbconnect
import threading

DEBUG = False

class OperationalError (Exception):
	pass


class SynConnect (dbconnect.DBConnect):
	def __init__ (self, address, params = None, lock = None, logger = None):
		dbconnect.DBConnect.__init__ (self, address, params, lock, logger)
		self.connected = False
	
	def connect (self):
		try:
			self.conn = sqlite3.connect (self.address, check_same_thread = False)
			self.cur = self.conn.cursor ()
		except:
			self.handle_error ()
		else:	
			self.connected = True
	
	def close (self):
		self.connected = False
		dbconnect.DBConnect.close (self)
	
	def close_case (self):
		if DEBUG: 
			self.__history.append ("END TRAN") 
			self.__history = self.__history [-30:]
		dbconnect.DBConnect.close_case (self)
				
	def execute (self, sql, callback):
		self.callback = callback
		self.has_result = False
		self.exception_str = ""
		self.exception_class = None		
		self.set_event_time ()		
		self.execute_count += 1		
		
		if not self.connected:
			self.connect ()
		
		tranaction = False
		sql= sql.strip ()
		try:
			if sql [:7].lower () == "select ":
				self.cur.execute (sql)
			else:	
				tranaction = True
				self.cur.executescript (sql)
		except:
			if tranaction: self.conn.rollback ()
			self.handle_error ()
		else:
			if tranaction: self.conn.commit ()
			self.has_result = True		
			self.close_case ()
		