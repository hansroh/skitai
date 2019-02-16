from rs4.producers import simple_producer
from aquests.athreads import trigger
from skitai.http_response import catch

class _Method:
	def __init__(self, send, name, caller = None):
		self.__send = send
		self.__name = name
		self.__caller = caller
		
	def __getattr__(self, name):
		return _Method (self.__send, "%s.%s" % (self.__name, name))
		
	def __call__(self, *args, **karg):
		karg ["caller"] = self.__caller		
		return self.__send (self.__name, args, karg)


class Promise (simple_producer):
	def __init__ (self, was, handler, **karg):
		self._was = was
		self.was = was._clone ()
		self.handler = handler
		
		self._data = []
		self._parts = karg
		self._numreq = 0
		self._numres = 0
		self._done = False
		self._rejected = 0
	
	def __getattr__ (self, name):
		if name.split (".")[0] not in self._was.METHODS:
			return getattr (self.was, name)
		self._numreq += 1
		return _Method (self._call, name)
		
	def _call (self, method, args, karg):
		if not karg.get ('meta'):
			karg ['meta'] = {}
		karg ['meta'] = {'__reqid': args [0]}
		karg ['callback'] = self
		return self._was._call (method, args [1:], karg)
		
	def __call__ (self, response):
		if self._done:
			return
		self._numres += 1
		response.id = response.meta ["__reqid"]
		try:
			self.handler (self, response)
		except:
			self.was.traceback ()
			self.reject ("<div style='padding: 8px; border: 1px solid #000; background: #efefef;'><h1>Error Occured While Processing</h1>%s</div>" % (self.was.app.debug and catch (1) or "",))
		
	def __setitem__ (self, name, data):
		self._parts [name] = data
	
	def __getitem__ (self, name, default = None):
		return self._parts.get (name, default)
	
	def set (self, k, v):
		self [k] = v
		
	def encode (self, d):
		if type (d) is bytes:
			return d			
		return str (d).encode ('utf8')		
		
	def send (self, data):
		if self._done:
			return		
		self._data.append (self.encode (data))
		if self.was.env ['wsgi.multithread']:
			trigger.wakeup ()
				
	def render (self, template_file, _do_not_use_this_variable_name_ = {}, **karg):	
		if not _do_not_use_this_variable_name_ and not karg:
			return self.was.render (template_file, self._parts)
		return self.was.render (template_file, _do_not_use_this_variable_name_, **karg)
	
	#-----------------------------------------------------
	
	def __len__ (self):
		return self._numreq
		
	def fulfilled (self):
		return self._numreq == self._numres
		
	def pending (self):
		return not self._done
		
	def rejected (self):
		return self._rejected
	
	def settled (self):
		return self.fulfilled () and self._done
				
	def settle (self, data = None):
		if data:			
			self.send (data)			
		self._done = True
	
	def reject (self, data):
		self._rejected = 1
		self.settle (data)
	
	#-------------------------------------------------
	
	def exhausted (self):
		return self._done and not self._data
					
	def ready (self):
		return self._data or self._done
		
	def more (self):		
		if self.exhausted ():
			return b''
		d, self._data = b''.join (self._data), []
		return d

		