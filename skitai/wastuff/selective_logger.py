from rs4.misc import producers
import threading
import os

class SelectiveLogger:
	MAX_CACHE = 1000

	def __init__ (self, log_off = []):
		self.log_off = log_off
		self.endswiths = []
		self.startswiths = []
		self.cache = {}
		self.lock = threading.RLock ()
		for each in log_off:
			if each.startswith ("*"):
				self.endswiths.append (each [1:])
			elif each.endswith ("*"):
				self.startswiths.append (each[:-1])
			else:
				self.startswiths.append (each)

	def add_cache (self, key, val):
		with self.lock:
			if len (self.cache) > self.MAX_CACHE:
				return
			self.cache [key] = val

	def loggable (self, uri):
		if not self.log_off or uri == "/":
			return True

		with self.lock:
			cached = self.cache.get (uri)
		if cached == -1:
			return False

		for each in self.endswiths:
			if uri.endswith (each):
				self.add_cache (uri, -1)
				return False

		d = os.path.dirname (uri)
		with self.lock:
			cached = self.cache.get (d)
		if cached == -1:
			return False
		elif cached == 1:
			return True

		for each in self.startswiths:
			if uri.startswith (each):
				self.add_cache (d, -1)
				return False

		self.add_cache (d, 1)
		return True

	def __call__ (self, uri, producer, logfunc):
		if self.loggable (uri):
			return producers.hooked_producer (producer, logfunc)
		return producer
