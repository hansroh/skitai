import threading
import time

class Storage:
	def __init__ (self):
		self.__d = {}
		self.__lock = threading.Lock ()
	
	def __contains__ (self, k):
		with self.__lock:
			return k in self.__d
		
	def set (self, k, v, timeout = 0):	
		with self.__lock:
			self.__d [k] = (v, timeout and time.time () + timeout or 0)
			
	def get (self, k, d = None):
		with self.__lock:
			try: v, expires = self.__d [k]
			except KeyError: return d	
							
		if expires and time.time () > expires:
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
	