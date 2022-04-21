# -*- Mode: Python; tab-width: 4 -*-

VERSION_STRING = "$Id: select_trigger.py,v 1.11 1999/07/27 00:05:21 rushing Exp $"

from rs4 import asyncore
from rs4 import asynchat
import time
import os
import socket
import string
import threading

class base_trigger:
	WAIT_TRIGGER = 0.02 # 20ms

	def __init__ (self, logger = None):
		self.logger = logger
		self.lock = threading.RLock ()
		self.thunks = []
		self.waiting = False

	def __repr__ (self):
		return '<select-trigger at %x>' % id (self)

	def readable (self):
		return 1

	def writable (self):
		return 0

	def handle_connect (self):
		pass

	def handle_read (self):
		self.recv (4096)
		with self.lock:
			thunks, self.thunks = self.thunks, []

		for thunk in thunks:
			try:
				thunk ()
			except:
				if self.logger:
					self.logger.trace ('the_trigger')

	def pull_trigger (self, thunk = None):
		with self.lock:
			if thunk:
				self.thunks.append (thunk)
			if self.waiting:
				return
			self.waiting = True

		# this is not for improving performance
		# it reduces response time when low load but also reduces server CPU load if high network load
		# Sep 13, 2020, Roh
		time.sleep (self.WAIT_TRIGGER)
		with self.lock:
			self.waiting = False
		self.shut () # KEEP this order, release and shut!


if os.name == 'posix':
	# Wake up a call to select() running in the main thread
	class trigger (base_trigger, asyncore.file_dispatcher):
		def __init__ (self, logger = None):
			base_trigger.__init__ (self, logger)
			r, w = os.pipe()
			self.trigger = w
			asyncore.file_dispatcher.__init__ (self, r)

		def shut (self):
			os.write (self.trigger, b'x')

else:
	# win32-safe version
	class trigger (base_trigger, asyncore.dispatcher):
		address = ('127.9.9.9', 19999)
		def __init__ (self, logger = None):
			base_trigger.__init__ (self, logger)
			sock_class = socket.socket
			a = sock_class (socket.AF_INET, socket.SOCK_STREAM)
			w = sock_class (socket.AF_INET, socket.SOCK_STREAM)
			try:
				a.setsockopt (
					socket.SOL_SOCKET, socket.SO_REUSEADDR, a.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) | 1
				)
			except socket.error:
				pass

			# tricky: get a pair of connected sockets
			a.bind (self.address)
			a.listen (1)
			w.setblocking (0)
			try: w.connect (self.address)
			except: pass

			r, addr = a.accept()
			a.close()
			w.setblocking (1)
			self.trigger = w
			asyncore.dispatcher.__init__ (self, r)

		def shut (self):
			self.trigger.send (b'x')
