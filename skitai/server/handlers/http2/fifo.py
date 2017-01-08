import threading

class priority_producer_fifo:
	def __init__ (self):
		self.l = []
		self.r = []
		self.has_None = False
		self._lock = threading.Lock ()
	
	def __len__ (self):
		with self._lock:
			l = len (self.l)
		if l:
			return l
					
		l = 0
		with self._lock:
			if self.r:
				for item in self.r:
					if item.ready ():
						return 1
		
		if not self.l and not self.r and self.has_None:
			# for return None
			self.l.append (None)
			return 1
		return 0
			
	def __getitem__(self, index):
		if index != 0:
			with self._lock:
				return self.l [index]
			
		with self._lock:
			if self.l and hasattr (self.l [0], 'ready') and not self.l [0].ready ():
				item = self.l.pop (0)
				self.r.append (item)
		
			if not self.l and self.r:
				# self.l always has got a priority
				for index in range (len (self.r)):
					item = self.r [index]
					if item.ready ():
						item = self.r.pop (index)
						self.l.insert (0, item)
						break
			
			if not self.l:
				self.l.append (b"")
			return self.l [0]
				
	def __setitem__(self, index, item):
		with self._lock:
			self.l.insert (index, item)
		
	def __delitem__ (self, index):
		import threading
		with self._lock:
			#print ('\n-------------', id(self), threading.currentThread())
			del self.l [index]
	
	def remove_from (self, stream_id, lst):
		deletables = []
		deleted = 0
		with self._lock:
			for index in range (len (lst)):
				try:
					producer_stream_id = lst [index].stream_id
				except AttributeError:
					pass
				else:
					if producer_stream_id	== stream_id:
						deletables.append (index)
			deleted = 1
			for index in deletables:
				item = lst.pop (index)
				if hasattr (item, 'close'):
					try: item.close ()
					except: pass
		return deleted
							
	def remove (self, stream_id):
		self.remove_from (stream_id, self.l)
		self.remove_from (stream_id, self.r)
	
	def append (self, item):		
		self.insert (-1, item)
	
	def appendleft (self, item):
		self.insert (0, item)
			
	def insert (self, index, item):
		if item is None:
			self.has_None = True
			return
			
		if self.has_None:
			return # deny adding	
		
		if hasattr (item, 'ready'):
			with self._lock:
				self.r.insert (index, item)
			return
					
		try:
			w1 = item.weight
			d1 = item.depends_on
		except AttributeError:
			with self._lock:
				self.l.insert (index, item)
			return
		
		index = 0
		inserted = False
		with self._lock:
			for each in self.l:
				try:
					w2 = each.weight
					d2 = each.depends_on
				except AttributeError:
					pass
				else:
					if d2 >= d1 and w2 < w1:
						self.l.insert (index, item)
						inserted = True
						break
				index += 1
		
		if not inserted:
			with self._lock:
				self.l.insert (index, item)
	
	def clear (self):
		with self._lock:
			self.l = []
			self.r = []
	
	