import threading
import time

class Storage:
	def __init__ (self, d = {}):
		self.__d = d
		self.__lock = threading.RLock ()
	
	def __len__ (self):
		return len (self.__d)
		
	def __contains__ (self, k):
		with self.__lock:
			return k in self.__d
	
	def __setitem__ (self, k, v):
		self.set (k, v)
	
	def __getitem__ (self, k):
		with self.__lock:
			return self.__d [k]
	
	def __delitem__ (self, k):
		self.remove (k)
		
	def new_storage (self, k, d = {}):
		self.set (k, Storage (d))
		
	def set (self, k, v, timeout = 0):	
		with self.__lock:
			self.__d [k] = (v, timeout and time.time () + timeout or 0)
			
	def get (self, k, d = None):
		with self.__lock:
			try: v, expires = self.__d [k]
			except KeyError: return d	

		if expires and time.time () >= expires:
			self.remove (k)
			return d
			
		return v	
	
	def clear (self):
		with self.__lock:
			self.__d = {}
		
	def remove (self, k):
		with self.__lock:
			try:
				self.__d.pop (k)
			except KeyError:
				pass	
	
	def keys (self):
		with self.__lock:
			return self.__d.keys ()
	
	def values (self):
		with self.__lock:
			return self.__d.values ()
			
	def items (self):
		with self.__lock:
			return self.__d.items ()
	
	def has_key (self, k):
		with self.__lock:
			return self.__d.has_key (k)
	