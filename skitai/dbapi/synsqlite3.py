import sqlite3
from . import dbconnect
import threading

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
	
	def execute (self, sql, callback):
		self.callback = callback
		self.has_result = False
		self.exception_str = ""
		self.exception_class = None		
		self.set_event_time ()		
		self.execute_count += 1		
		
		if not self.connected:
			self.connect ()

		sql= sql.strip ()
		try:
			if sql [:7].lower () == "select ":
				self.cur.execute (sql)
			else:	
				self.cur.executescript (sql)				
		except:
			self.handle_error ()
		else:
			self.conn.commit ()
			self.has_result = True		
			self.close_case ()
		