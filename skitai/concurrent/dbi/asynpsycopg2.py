#-------------------------------------------------------
# Asyn PostgresSQL Dispatcher
# Hans Roh (hansroh@gmail.com)
# 2015.6.9
#-------------------------------------------------------
from rs4 import asyncore
from . import dbconnect
import sys
import threading

DEBUG = False
REREY_TEST = False

class AsynConnect (dbconnect.AsynDBConnect, asyncore.dispatcher):
	def __init__ (self, address, params = None, lock = None, logger = None):
		dbconnect.AsynDBConnect.__init__ (self, address, params, lock, logger)
		self.cur = None
		self.retries = 0
		asyncore.dispatcher.__init__ (self)

	def retry (self):
		if self.request is None:
			return
		self.retries += 1
		self.logger ("[warn] closed psycopg2 connection, retrying...")
		self.disconnect ()
		request, self.request = self.request, None
		self.execute (request)
		return _STATE_RETRY

	def poll (self):
		try:
			try:
				if REREY_TEST and self.writable () and self.request.retry_count == 0:
					self.disconnect ()
				state = self.socket.poll ()
				if state not in _STATE_OK:
					self.logger ("[warn] psycopg2.poll() returned %s" % state)
					return self.handle_expt ()
				return state

			except (psycopg2.OperationalError, psycopg2.InterfaceError):
				if self.request:
					if self.request.retry_count == 0:
						self.request.retry_count += 1
						return self.retry ()
				raise

		except:
			self.handle_error ()

	def writable (self):
		return self.out_buffer or not self.connected

	def readable (self):
		return self.connected and not self.out_buffer

	def add_channel (self, map = None):
		return asyncore.dispatcher.add_channel (self, map)

	def del_channel (self, map=None):
		dbconnect.AsynDBConnect.del_channel (self, map)

	def handle_expt_event (self):
		self.handle_expt ()

	def handle_connect_event (self):
		if self.poll () == POLL_OK:
			self.handle_connect ()
			self.connected = True
			self.connecting = False

	def handle_write_event (self):
		if not self.connected:
			self.handle_connect_event ()
		else:
			self.handle_write ()

	def handle_expt (self):
		self.handle_close (psycopg2.OperationalError ("Socket Panic"))

	def handle_connect (self):
		self.create_cursor ()

	def handle_read (self):
		if self.cur and self.poll () == POLL_OK:
			self.set_event_time ()
			self.has_result = True
			self.close_case (commit = True)

	def handle_write (self):
		if self.poll () == POLL_OK:
			if self.cur is None:
				self.create_cursor ()
			self.set_event_time ()
			try:
				self.cur.execute (self.out_buffer)
			except:
				self.handle_error ()
			self.out_buffer = ""

	#-----------------------------------
	# Overriden
	#-----------------------------------
	def create_cursor (self):
		if self.cur is None:
			try:
				self.cur = self.socket.cursor ()
			except:
				self.handle_error ()

	def close_cursor (self):
		if self.cur:
			try: self.cur.close ()
			except: pass
			self.cur = None

	def close (self):
		self.close_cursor ()
		asyncore.dispatcher.close (self)
		dbconnect.AsynDBConnect.close (self)

	def close_case (self, commit = False):
		if self.request:
			description, data = self.cur and self.cur.description or None, None
			if description:
				try:
					data = self.fetchall ()
				except:
					self.logger.trace ()
					self.expt = asyncore.compact_traceback () [2]
					data = None
			self.request.handle_result (description or None, self.expt, data)
		dbconnect.AsynDBConnect.close_case (self, commit)

	def end_tran (self):
		self.close_cursor ()
		dbconnect.AsynDBConnect.end_tran (self)

	def fetchall (self):
		data = self.cur.fetchall ()
		self.result = False
		return data

	def connect (self, force = 0):
		self.connecting = True
		self.connected = False
		host, port = self.address
		sock = psycopg2.connect (
			dbname = self.dbname,
			user = self.user,
			password = self.password,
			host = host,
			port = port,
			async_ = 1
		)
		self.set_socket (sock)

	def _compile (self, request):
		sql = request.params [0]
		if isinstance (sql, (list, tuple)):
			sql = ";\n".join (map (str, sql)) + ";"
		try:
			sql = sql.strip ()
		except AttributeError:
			raise dbconnect.SQLError ("Invalid SQL")
		if not sql:
			raise dbconnect.SQLError ("Empty SQL")
		return sql

	def execute (self, request, *args, **kargs):
		dbconnect.DBConnect.begin_tran (self, request)
		self.out_buffer = self._compile (request)
		if not self.connected and not self.connecting:
			return self.connect ()
		if self.poll () == POLL_OK:
			self.create_cursor ()


_AsynConnect = AsynConnect # for subclassing

try:
	if '__pypy__' in sys.builtin_module_names:
		from psycopg2cffi import compat
		compat.register()
	import psycopg2

except ImportError:
	from rs4.annotations import Uninstalled
	AsynConnect = Uninstalled ('psycopg2')

else:
	from psycopg2.extensions import POLL_OK, POLL_READ, POLL_WRITE

	_STATE_OK = (POLL_OK, POLL_READ, POLL_WRITE)
	_STATE_RETRY = -1
