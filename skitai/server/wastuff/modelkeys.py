import multiprocessing

class ModelKeys:
	def __init__ (self, keys):
		self._keys  = keys
		self._arr = multiprocessing.Array ('d', [0.0] * len (keys), lock = multiprocessing.RLock ())		
		self._d = {}
		for i in range (len (keys)):
			self._d [keys [i]] = i
	
	def __len__ (self):
		return len (self.__d)
		
	def __contains__ (self, k):
		with self.__lock:
			return k in self.__d
			
	def __setitem__ (self, k, v):
		self.set (k, v)
	
	def __getitem__ (self, k):
		return self._d [k]
		
	def set (self, k, v, ignore_nokey = False):
		try:
			self._arr [self._d [k]] = v
		except KeyError:
			if not ignore_nokey:
				raise
	
	def get (self, k, d = None):
		try:
			v = self._arr [self._d [k]]
		except KeyError:
			return d
		return v or d
	
	def keys (self):
		return self._keys [:]
	
	def values (self):
		t = []
		for i in range (len (self._keys)):
			t.append (self._arr [i])
		return t
			
	def items (self):
		t = []
		for i in range (len (self._keys)):
			t.append ((self._keys [i], self._arr [i]))
		return t
	
	def has_key (self, k):
		return self.__d.has_key (k)
