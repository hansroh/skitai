class UDict:
	def __init__ (self):
		self.__d__ = {}
	
	def as_dict (self):
		return self.__d__
		
	def __str__ (self):
		return str (self.__d__)
		
	def __getattr__ (self, attr):
		try:
			return self.__d__ [attr]
		except KeyError:
			raise AttributeError

	def __setattr__ (self, attr, val):
		if attr != "__d__":
			self.__d__ [attr] = val
		else:
		        self.__dict__ ["__d__"] = val

	def __delattr__ (self, attr):
		try:
			del self.__d__ [attr]
		except KeyError:
			raise AttributeError

	def __setitem__ (self, attr, val):
		self.__d__ [attr] = val

	def __getitem__ (self, key):
		return self.__d__ [key]

	def __delitem__ (self, key):
		del self.__d__ [key]
		
	def keys (self):
		return self.__d__.keys ()

	def items (self):
		return self.__d__.items ()

	def has_key (self, key):
		return self.__d__.has_key (key)

	def get (self, key, default):
		if not self.__d__.has_key (key):
			return default
		else:
			return self.__d__ [key]
