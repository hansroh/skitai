from aquests.lib.producers import simple_producer
from aquests.lib.athreads import trigger

class _Method:
	def __init__(self, send, name):
		self.__send = send
		self.__name = name
		
	def __getattr__(self, name):
		return _Method(self.__send, "%s.%s" % (self.__name, name))
		
	def __call__(self, *args, **karg):		
		return self.__send(self.__name, args, karg)


class FakeWAS: 
	def __init__ (self, was):
		self.env = was.env
		self.request = was.request
		self.app = was.app
		self.ab = was.ab
		if hasattr (was, 'g'):
			self.g = was.g
		
class AsyncResponse (simple_producer):
	def __init__ (self, was, handler):
		self.__was = was
		self.was = FakeWAS (was)
		self.handler = handler
		self.app_renderer = was.app.render
		
		self._data = None
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
		karg ['callback'] = self
		karg ['meta'] = {'name': args [0]}
		self.__was._call (method, args [1:], karg)
		
	def __call__ (self, response):
		self._numres += 1
		self.handler (response.meta ["name"], response, self)
	
	def __setitem__ (self, name, data):
		self._parts [name] = data
	
	def __getitem__ (self, name, default = None):
		return self._parts.get (name, default)
		
	def ready (self):
		return self._done
		
	def more (self):		
		if not self._data:
			return b''
		d, self._data = self._data, None
		return d
	
	def fetched_all (self):
		return self._numreq == self._numres

	def render (self, template_file, _do_not_use_this_variable_name_ = {}, **karg):		
		return self.app_renderer (self.was, template_file, _do_not_use_this_variable_name_, **karg)
	
	def render_all (self, template_file):
		return self.render (template_file, self._parts)
			
	def push (self, data):
		self._data = data
		if type (self._data) is str:
			self._data = self._data.encode ('utf8')
		self._done = True
		if self.was.env ['wsgi.multithread']:
			trigger.wakeup ()
		