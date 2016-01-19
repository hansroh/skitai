from skitai.server  import utility
from . import cookie
from skitai.lib.reraise import reraise 
import sys
from skitai.server.threads import trigger

def traceback ():	
	t, v, tb = sys.exc_info ()
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
	def __init__ (self, env, get_method):
		self.env = env	
		self.get_method = get_method
		self.was = None
	
	def exec_chain (self, func, first_expt = None):
		try:
			func (self.was)		
		except Exception as expt:
			self.was.logger.trace ("app")
			if first_expt is None: 
				return sys.exc_info ()		
		return first_expt
				
	def chained_exec (self, method, args, karg):
		# recursive before, after, teardown
		# [b, [b, [b, func, s, f, t], s, f, t], s, f, t]
		
		response = None
		first_expt = None
		
		[before, func, success, failed, teardown] = method
		_ok, _exception, _teardown = None, None, None
		
		try:
			if before:
				response = before (self.was)
				if response:
					return response
			
			if type (func) is list:
				response = self.chained_exec (func, args, karg)					
					
			else:
				response = func (self.was, *args, **karg)
				if type (response) is not list:
					response = [response]											
				# ok, exception, teardown
				_ok, _exception, _teardown = self.was.temp._binds [:3]
				
		except MemoryError:
			raise
																										
		except Exception as expt:
			self.was.logger.trace ("app")
			if first_expt is None: first_expt = sys.exc_info ()
			
			if _exception:		self.exec_chain (_exception)
			if failed:		self.exec_chain (failed)
							
		else:
			if _ok: 	first_expt = self.exec_chain (_ok)
			if success: 	first_expt = self.exec_chain (success)
		
		if _teardown: 	first_expt = self.exec_chain (_teardown, first_expt)
		if teardown: 		first_expt = self.exec_chain (teardown, first_expt)
			
		if first_expt:
			reraise (*first_expt)
		
		return response
		
	def generate_content (self, method, _args, karg):		
		_karg = self.parse_kargs (karg)		
		response = self.chained_exec (method, _args, _karg)
		return response
	
	def parse_kargs (self, kargs):
		allkarg = {}
		query = self.env.get ("QUERY_STRING")
		data = None
		_input = self.env ["wsgi.input"]
		if _input:
			if type (_input) is dict: # multipart
				self.merge_args (allkarg, _input)
			else:
				data = _input.read ()
		
		if kargs:
			self.merge_args (allkarg, kargs)
		if query: 
			self.merge_args (allkarg, utility.crack_query (query))
		if data:
			self.merge_args (allkarg, utility.crack_query (data))
			
		return allkarg
		
	def merge_args (self, s, n):
		for k, v in list(n.items ()):
			if k in s:
				if type (s [k]) is not list:
					s [k] = [s [k]]
				s [k].append (v)
			else:	 
				s [k] = v
	
	def build_was (self):
		class Temp:
			def __init__ (self):
				self._binds = [None] * 3
				
			def bind (self, index, method):
				self._binds [index] = method
				
		_was = self.env["skitai.was"]
		_was.env = self.env
		_was.temp = Temp ()
		_was.response = _was.request.response
		_was.cookie = cookie.Cookie (_was.request, _was.app.securekey, _was.app.session_timeout)
		_was.session = _was.cookie.get_session ()
		self.was = _was		
	
	def commit (self):
		# keep commit order, session -> cookie
		try: self.was.session.commit ()
		except AttributeError: pass							
		self.was.cookie.commit ()
			
	def __call__ (self):	
		thing, param = self.get_method (self.env ["PATH_INFO"])
		if thing is None:
			# Middleware Just push (), Skitai DO done().
			self.env[ "skitai.was"].request.response.send_error ("404 Not Found")
			return b""
		
		if param == 301:
			response = self.env ["skitai.was"].request.response
			location = self.env ["SCRIPT_NAME"] + thing
			response ["Location"] = location
			response.send_error ("301 Object Moved", why = 'Object Moved To <a href="%s">Here</a>' % location)
			return b""
		
		self.build_was ()
		content = self.generate_content (thing, (), param)
		self.commit ()
		return content
		