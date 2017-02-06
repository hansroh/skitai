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


class ResProxy (simple_producer):
	def __init__ (self, was, handler):
		self.__was = was
		self.was = was._clone ()		
		self.handler = handler
		
		self._data = []
		self._parts = {}
		self._numreq = 0
		self._numres = 0
		self._done = False
	
	def __getattr__ (self, name):
		if name.split (".")[0] not in self.__was.VALID_COMMANDS:
			raise AttributeError ('%s is not member' % name)
		self._numreq += 1
		return _Method(self._call, name)
	
	def _call (self, method, args, karg):
		if not karg.get ('meta'):
			karg ['meta'] = {}
		karg ['meta'] = {'__reqid': args [0]}
		karg ['callback'] = self
		self.__was._call (method, args [1:], karg)
		
	def __call__ (self, response):
		self._numres += 1
		response.reqid = response.meta ["__reqid"]
		try:
			self.handler (response, self)
		except:
			self.was.traceback ()
			self.done ("<div style='padding: 8px; border: 1px solid #000; background: #efefef;'><h1>Error Occured While Processing</h1>%s</div>" % (self.was.app.debug and catch (1) or "",))
	
	def __setitem__ (self, name, data):
		self._parts [name] = data
	
	def __getitem__ (self, name, default = None):
		return self._parts.get (name, default)
		
	def ready (self):
		return self._data or self._done
		
	def more (self):		
		if self._done and not self._data:
			return b''
		d, self._data = b''.join (self._data), []
		return d
	
	def fetched_all (self):
		return self._numreq == self._numres

	def render (self, template_file, _do_not_use_this_variable_name_ = {}, **karg):		
		return self.was.render (template_file, _do_not_use_this_variable_name_, **karg)
	
	def render_all (self, template_file):
		return self.render (template_file, self._parts)
	
	def done (self, data = None):
		if data:
			self.push (data)
		self._done = True		
				
	def push (self, data):
		if self._done:
			return
		if type (data) is str:
			data = data.encode ('utf8')
		self._data.append (data)
		if self.was.env ['wsgi.multithread']:
			trigger.wakeup ()
		