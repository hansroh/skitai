import threading
import asyncore

class thread_safe_socket_map (dict):
	def __init__ (self):
		self.lock = threading.Lock ()
	
	def __setitem__ (self, k, v):	
		self.lock.acquire ()
		dict.__setitem__ (self, k, v)
		self.lock.release ()
		
	def __getitem__ (self, k):	
		self.lock.acquire ()
		v = dict.__getitem__ (self, k)
		self.lock.release ()
		
	def __delitem__ (self, k):
		self.lock.acquire ()
		try:
			dict.__delitem__ (self, k)	
		finally:
			self.lock.release ()
	
	def has_key (self, k):
		self.lock.acquire ()
		v = dict.has_key (self, k)
		self.lock.release ()
		return v
			
	def get (self, k, d = None):
		self.lock.acquire ()
		v = dict.get (self, k, d)
		self.lock.release ()
		return v
	
	def items (self):
		self.lock.acquire ()
		v = dict.items (self)
		self.lock.release ()
		return v
			
	def keys (self):
		self.lock.acquire ()
		v = dict.keys (self)
		self.lock.release ()
		return v
	
	def values (self):
		self.lock.acquire ()
		v = dict.values (self)
		self.lock.release ()
		return v


if not hasattr (asyncore, "_socket_map"):
	asyncore._socket_map = asyncore.socket_map
	del asyncore.socket_map
	asyncore.socket_map = thread_safe_socket_map ()
