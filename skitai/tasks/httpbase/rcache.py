from hashlib import md5
import time
import threading

class Result:
	def __init__ (self, status, ident = None):
		self.status = status
		self.ident = ident

		self.timeout = 0
		self.cached_time = 0
		self.remain_secs = 0
		self.is_cached = False

	def is_normal (self):
		return self.status == 3

	def get_status (self):
		# 0: Not Connected
		# 1: Operation Timeout
		# 2: Exception Occured
		# 3: Normal
		return self.status

	def set_status (self, status):
		self.status = status

	def cache (self, timeout = 300):
		global the_rcache

		if timeout <= 0:
			return self.expire ()

		if self.is_cached:
			return

		if the_rcache is None or self.status != 3 or not self.ident:
			return

		self.timeout = timeout
		self.cached_time = time.time ()
		the_rcache.cache (self)

	def expire (self):
		global the_rcache

		if not self.is_cached:
			return
		the_rcache.expire (self)


class RCache:
	def __init__ (self, maxobj = 2000):
		self.__cache = {}
		self.maxobj = maxobj
		self.num_clear = int (self.maxobj * 0.2)
		self.lock = threading.RLock ()

		self.cached = 0
		self.reqs = 0
		self.hits = 0

	def __len__ (self):
		return len (self.__cache)

	def hash (self, hashable):
		return md5 (hashable.encode ("utf8")).hexdigest ()

	def maintern (self):
		# remove 20% if reach max count
		t = list(self.__cache.items ())
		t.sort (key = lambda x: x [1].remain_secs)
		for h, obj in t [:self.num_clear]:
			del self.__cache [h]

	def cache (self, obj):
		with self.lock:
			clen = len (self.__cache)

		if clen == self.maxobj:
			with self.lock:
				self.maintern ()

		h = self.hash (obj.ident)
		with self.lock:
			if h not in self.__cache:
				obj.remain_secs = obj.timeout
				obj.is_cached = True
				self.__cache [h] = obj
				self.cached += 1

	def get (self, hashable, last_update = 0):
		h = self.hash (hashable)

		self.lock.acquire ()
		self.reqs += 1
		try:
			obj = self.__cache [h]
		except KeyError:
			self.lock.release ()
			return None
		self.lock.release ()

		try:
			last_update_ = int (last_update)
		except:
			last_update = 0.0
		else:
			if last_update_ == 1:
				last_update = 0.0

		if last_update and last_update > obj.cached_time:
			with self.lock:
				try: del self.__cache [h]
				except KeyError: pass
			return None

		passed = time.time () - obj.cached_time
		if passed > obj.timeout:
			with self.lock:
				try: del self.__cache [h]
				except KeyError: pass
			return None

		with self.lock:
			obj.remain_secs = obj.timeout - passed
			self.hits += 1

		return obj

	def expire (self, obj):
		with self.lock:
			h = self.hash (obj.ident)
			try: h.close ()
			except AttributeError: pass
			try: del self.__cache [h]
			except KeyError: pass

	def ratio (self):
		if self.reqs:
			ratio = "%2.1f %%" % (1.0 * self.hits / self.reqs * 100.,)
		else:
			ratio = "N/A"

	def status (self):
		with self.lock:
			d = {
				"current_cached": len (self.__cache),
				"cached": self.cached,
				"hits": self.hits,
				"requests": self.reqs,
				"hits_success_ratio": self.ratio ()
			}

		return d

the_rcache = None

def start_rcache (maxobj = 2000):
	global the_rcache
	if the_rcache is None:
		the_rcache = RCache (maxobj)

