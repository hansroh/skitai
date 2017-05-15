from aquests.lib.producers import simple_producer
from aquests.lib.athreads import trigger
from skitai.server.http_response import catch

class _Method:
	def __init__(self, send, name):
		self.__send = send
		self.__name = name
		
	def __getattr__(self, name):
		return _Method(self.__send, "%s.%s" % (self.__name, name))
		
	def __call__(self, *args, **karg):		
		return self.__send(self.__name, args, karg)


class Promise (simple_producer):
	def __init__ (self, was, handler, prolog = None, epilog = None):
		self.__was = was
		self.was = was._clone ()
		self.handler = handler
		self.prolog = self.encode (prolog)
		self.epilog = self.encode (epilog)
		
		self._data = []
		self._parts = {}
		self._numreq = 0
		self._numres = 0
		self._done = False
		self._rejected = 0
	
	def __getattr__ (self, name):
		if name.split (".")[0] not in self.__was.VALID_COMMANDS:
			raise AttributeError ('%s is not member' % name)
		self._numreq += 1
		return _Method (self._call, name)
	
	def _call (self, method, args, karg):
		if not karg.get ('meta'):
			karg ['meta'] = {}
		karg ['meta'] = {'__reqid': args [0]}
		karg ['callback'] = self
		self.__was._call (method, args [1:], karg)
		
	def __call__ (self, response):
		if self._done:
			return
		self._numres += 1
		response.reqid = response.meta ["__reqid"]
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
		if type (d) is str:
			return d.encode ('utf8')
		return d
	
	def send (self, data):
		if self._done:
			return
		if self.prolog:
			self._data.append (self.prolog)
			self.prolog = None
		self._data.append (self.encode (data))
		if self.was.env ['wsgi.multithread']:
			trigger.wakeup ()
				
	def render (self, template_file, _do_not_use_this_variable_name_ = {}, **karg):	
		if not _do_not_use_this_variable_name_ and not karg:
			return self.render (template_file, self._parts)
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
			
		if self.epilog:
			self._data.append (self.epilog)
			self.epilog = None
			
		self._done = True
	
	def reject (self, data):
		self._rejected = 1
		self.settle (data)
	
	#-------------------------------------------------
					
	def ready (self):
		return self._data or self._done
		
	def more (self):		
		if self._done and not self._data:
			return b''
		d, self._data = b''.join (self._data), []
		return d

		