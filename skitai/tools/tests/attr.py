class _Method:
	def __init__(self, send, name):
		self.__send = send
		self.__name = name
		
	def __getattr__(self, name):
		return _Method(self.__send, "%s.%s" % (self.__name, name))
		
	def __call__(self, *args):
		return self.__send(self.__name, args)


class A:
	def __getattr__ (self, name):	  
		return _Method(self._call, name)
		
	def _call (self, method, args):
		print method, args
		

		
		
		
		
a = A ()
a.put.map ()



		
		
	