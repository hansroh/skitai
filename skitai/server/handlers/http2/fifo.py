import threading

class priority_producer_fifo:
	def __init__ (self):
		self.l = []
		self._lock = threading.Lock ()
	
	def __len__ (self):
		with self._lock:
			l = len (self.l)
		return l
		
	def __getitem__(self, index):
		with self._lock:
			i = self.l [index]
		return i	
	
	def __setitem__(self, index, item):
		with self._lock:
			self.l.insert (index, item)
		
	def __delitem__ (self, index):	
		with self._lock:
			del self.l [index]
	
	def remove (self, stream_id):	
		index = 0
		with self._lock:
			for each in self.l:
				try:
					legacy_stream_id = each.stream_id
				except AttributeError:
					pass
				else:
					if legacy_stream_id	== stream_id:
						item = self.l.pop (index)
						if hasattr (item, 'close'):
							try: item.close ()
							except: pass
						break
				index += 1		
			
	def append (self, item):
		has_None = False
		with self._lock:
			if self.l and self.l [-1] is None:
				has_None = True
		if has_None:
			return
				
		if item is None:
			with self._lock:
				self.l.append (item)
			return
			
		try:
			w1 = item.weight
			d1 = item.depends_on
		except AttributeError:
			with self._lock:
				self.l.append (item)
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
				self.l.append (item)
			
	def appendleft (self, item):
		with self._lock:
			self.l.insert (0, item)
		
	def clear (self):
		with self._lock:
			self.l = []
	
	def ready (self):
		# check if remote flow control window for each stream is open
		# but maybe unnecessory and unused
		self._lock.acquire ()
		if not self.l:
			self._lock.release ()
			return False
			
		first = self.l [0]
		if not hasattr (first, 'stream_id') or first.ready ():
			self._lock.release ()
			return True
		
		index = 1
		has_ready = False
		for item in self.l [1:]:
			if not hasattr (item, 'stream_id'):
				break
							
			if item.ready ():
				ready_item = self.l.pop (index)
				self.l.insert (0, ready_item)
				has_ready = True
				break
				
			index += 1
		
		self._lock.release ()
		return has_ready
				