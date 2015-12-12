from skitai.server  import utility
from . import cookie
from skitai.lib.reraise import reraise 
import sys

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
	
	def chained_exec (self, method, args, karg):
		# recursive before, after, teardown
		# [b, [b, [b, func, s, f, t], s, f, t], s, f, t]
		
		response = None
		first_expt = None
		
		[before, func, success, failed, teardown] = method
		
		try:
			if before:
				response = before (self.was)
				if response:
					return response
			
			if type (func) is list:
				response = self.chained_exec (func, args, karg)					
					
			else:
				response = func (self.was, *args, **karg)
				
		except MemoryError:
			raise
																										
		except Exception as expt:
			self.was.logger.trace ("app")
			if first_expt is None: first_expt = sys.exc_info ()
			if failed:
				try:
					failed (self.was)		
				except Exception as expt:
					self.was.logger.trace ("app")
					if first_expt is None: first_expt = sys.exc_info ()
			
		else:
			if success: 
				try:
					success (self.was)
				except Exception as expt:
					self.was.logger.trace ("app")
					if first_expt is None: first_expt = sys.exc_info ()
		
		if teardown:
			try:
				teardown (self.was)
			except Exception as expt:
				self.was.logger.trace ("app")
				if first_expt is None: first_expt = sys.exc_info ()
		
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
		_was = self.env["skitai.was"]
		_was.env = self.env
		_was.response = _was.request.response
		_was.cookie = cookie.Cookie (_was.request)
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
			self.env[ "skitai.was"].request.response.error (404)
			return
		
		if param == 301:
			response = self.env ["skitai.was"].request.response
			location = self.env ["SCRIPT_NAME"] + thing
			response ["Location"] = location
			response.error (301, why = 'Object Moved To <a href="%s">Here</a>' % location)
			return 
		
		self.build_was ()
		content = self.generate_content (thing, (), param)
		self.commit ()
		
		return content
		