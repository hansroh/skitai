from skitai.server  import utility
from . import cookie
from skitai.lib.reraise import reraise 
import sys
	
def traceback ():	
	t, v, tb = exc_info
	tbinfo = []
	assert tb # Must have a traceback
	while tb:
		tbinfo.append((
			tb.tb_frame.f_code.co_filename,
			tb.tb_frame.f_code.co_name,
			str(tb.tb_lineno)
			))
		tb = tb.tb_next

	del tb
	file, function, line = tbinfo [-1]
	return (
		"%s %s, file %s at line %s, %s" % (
			t, v, file, line, 
			function == "?" and "__main__" or "function " + function
		)
	)

		
class Executor:
	def __init__ (self, env, start_response, get_method):
		self.env = env
		self.start_response = start_response
		self.get_method = get_method
		
		_was = self.env.get ("skitai.was")
		if _was:
			_was.app = _was.route.get_callable ()
			_was.response = _was.request.response
			_was.cookie = cookie.Cookie (_was.request)
			_was.session = _was.cookie.get_session ()
		self.was = _was
			
	def commit (self):
		# keep commit order, session -> cookie
		try: self.was.session.commit ()
		except AttributeError: pass							
		self.was.cookie.commit ()
	
	def chained_exec (self, method, args, karg):
		# recursive before, after, teardown
		# [b, [b, [b, func, s, f, t], s, f, t], s, f, t]
		
		response = None
		exc_info = None
		
		[before, func, success, failed, teardown] = method
		
		try:
			if before:
				response = before (was)
				if response:
					return response
			
			if type (func) is list:
				response = self.chained_exec (self.was, func, args, karg)					
					
			else:
				response = func (self.was, *args, **karg)
				
		except MemoryError:
			raise
																										
		except Exception as expt:
			self.was.logger.trace ("app")
			exc_info = sys.exc_info ()
			if failed:
				try:
					failed (self.was)		
				except:
					self.was.logger.trace ("app")
					exc_info = sys.exc_info ()
			
		else:
			if success: 
				try:
					success (self.was)
				except:
					self.was.logger.trace ("app")
					exc_info = sys.exc_info ()
		
		if teardown:
			try:
				response = teardown (self.was)
			except:
				self.was.logger.trace ("app")
				exc_info = sys.exc_info ()
		
		if exc_info:
			reraise (*exc_info)
		
		return response
		
	def generate_content (self, method, karg):		
		_args, _karg = self.parse_args (karg)		
		response = self.chained_exec (method, _args, _karg)
		
		return response
	
	def parse_args (self, kargs):
		allargs = {}
		allkarg = {}
		
		query = self.env.get ("QUERY_STRING")
		data = None
		_input = self.env ["wsgi.input"]
		if _input:
			if type (_input) is dict: # multipart
				self.merge_args (allkarg, _input)
			else:
				data = _input.read ()
				
		if query: 
			self.merge_args (allkarg, utility.crack_query (query))
		if data:
			self.merge_args (allkarg, utility.crack_query (data))
		return allargs, allkarg
		
	def merge_args (self, s, n):
		for k, v in list(n.items ()):
			if k in s:
				if type (s [k]) is not list:
					s [k] = [s [k]]
				s [k].append (v)
			else:	 
				s [k] = v
	
	def __call__ (self):	
		thing, param = self.get_method (self.env ["PATH_INFO"])
		if thing is None:
			self.start_response ("404 Not Found", [])
			return None		
		if param == 301:
			self.start_response ("301 Moved Permanently", [("Location", thing)])
			return None
		self.commit ()
		return self.generate_content (thing, param)
					
				
