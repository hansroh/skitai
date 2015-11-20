import multiprocessing

class counter:
	def __init__ (self, initial_value=0):
		self.value = initial_value
	
	def inc(self, delta=1):
		return self.increment(delta)
	
	def dec(self, delta=1):
		return self.decrement(delta)	
		
	def increment (self, delta=1):
		result = self.value
		try:
			self.value = self.value + delta
		except OverflowError:
			self.value = int(self.value) + delta
		return result

	def decrement (self, delta=1):
		result = self.value
		try:
			self.value = self.value - delta
		except OverflowError:
			self.value = int(self.value) - delta
		return result

	def as_long (self):
		return int (self.value)

	def __bool__ (self):
		return self.value != 0

	def __repr__ (self):
		return '<counter value=%s at %x>' % (self.value, id(self))

	def __str__ (self):
		return str(int(self.value))


class mpcounter:
	def __init__ (self, initial_value=0):
		self.value = multiprocessing.Value ("i", initial_value)
		self.lock = multiprocessing.Lock ()
		
	def inc(self, delta=1):
		return self.increment(delta)
	
	def dec(self, delta=1):
		return self.decrement(delta)	
		
	def increment (self, delta=1):
		self.lock.acquire ()
		try:
			result = self.value.value
			try:
				self.value.value = self.value.value + delta
			except OverflowError:
				self.value.value = int(self.value.value) + delta
		finally:
			self.lock.release ()					
		return result

	def decrement (self, delta=1):
		self.lock.acquire ()
		try:
			result = self.value.value
			try:
				self.value.value = self.value.value - delta
			except OverflowError:
				self.value.value = int(self.value.value) - delta
		finally:
			self.lock.release ()		
		return result

	def as_long (self):
		self.lock.acquire ()
		result = self.value.value
		self.lock.release ()
		return int (result)

	def __bool__ (self):
		self.lock.acquire ()
		result = self.value.value
		self.lock.release ()
		return result != 0

	def __repr__ (self):
		self.lock.acquire ()
		result = self.value.value
		self.lock.release ()
		return '<mpcounter value=%s at %x>' % (result, id(self))

	def __str__ (self):
		self.lock.acquire ()
		result = self.value.value
		self.lock.release ()
		return str(int(result))

if __name__ == "__main__":
	f = mpcounter (0)
	print(f.increment ())
	print(f.increment ())
	print(f.increment ())
	print(f.as_long ())
	print(str (f))
	print(f.decrement ())
	print(f.as_long ())
	print(str (f))
	
	
	

