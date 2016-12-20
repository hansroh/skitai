from skitai.server  import utility
from . import cookie
from skitai.lib.reraise import reraise 
import sys
from skitai.server.threads import trigger
from skitai.lib.attrdict import AttrDict

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
				if type (response) is not list:
					response = [response]											
				
		except MemoryError:
			raise
																										
		except Exception as expt:			
			self.was.logger.trace ("app")
			if failed:
				response = failed (self.was, sys.exc_info ())
			if response is None:				
				raise
							
		else:
			success and success (self.was)

		teardown and teardown (self.was)
		return response
		
	def generate_content (self, method, _args, karg):		
		_karg = self.parse_kargs (karg)		
		self.was.request.args = _karg
		response = self.chained_exec (method, _args, _karg)		
		return response
	
	def parse_kargs (self, kargs):
		allkarg = AttrDict ()
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
		class G:
			pass
			
		_was = self.env["skitai.was"]
		_was.env = self.env
				
		# these objects will be create just in time from _was.
		#_was.cookie = cookie.Cookie (_was.request, _was.app.securekey, _was.app.session_timeout)
		#_was.session = _was.cookie.get_session ()
		#_was.mbox = _was.cookie.get_notices ()
		#_was.g = G ()
		self.was = _was
	
	def commit (self):
		# keep commit order, session -> mbox -> cookie
		if not self.was.in__dict__ ("cookie"):		
			return			
		if self.was.in__dict__ ("session"):		
			self.was.session and self.was.session.commit ()
		if self.was.in__dict__ ("mbox"):
			self.was.mbox and self.was.mbox.commit ()
		self.was.cookie.commit ()
	
	def rollback (self):
		if not self.was.in__dict__ ("cookie"):		
			return			
		# keep commit order, session -> mbox -> cookie
		if self.was.in__dict__ ("session"):		
			self.was.session and self.was.session.rollback ()
		if self.was.in__dict__ ("mbox"):		
			self.was.mbox and self.was.mbox.rollback ()
		self.was.cookie.rollback ()
	
	responses = {
		404: "Not Found",
		415: "Unsupported Content Type",
		405: "Method Not Allowed"			
	}	
	
	def isauthorized (self, app, request):			
		try: 
			www_authenticate = app.authorize (request.get_header ("Authorization"), request.command, request.uri)
			if type (www_authenticate) is str:
				request.response ['WWW-Authenticate'] = www_authenticate
				request.response.send_error ("401 Unauthorized")
				return False				
			elif www_authenticate:
				request.user = www_authenticate
			else:	
				request.user = None
					
		except AttributeError: 
			pass
			
		return True
				
	def __call__ (self):		
		request = self.env ["skitai.was"].request
		
		current_app, thing, param, respcode = self.get_method (
			self.env ["PATH_INFO"], 
			request.command.upper (), 
			request.get_header ('content-type'),
			request.get_header ('authorization')
		)
		
		if respcode == 301:
			response = request.response
			response ["Location"] = thing
			response.send_error ("301 Object Moved", why = 'Object Moved To <a href="%s">Here</a>' % thing)
			return b""
		
		if respcode == 401:
			if not self.isauthorized (current_app, request):
				return b""
			# passed then be normal
			respcode = 0
			
		if respcode:
			request.response.send_error ("%d %s" % (respcode, self.responses.get (respcode, "Undefined Error")))
			return b""
			
		self.build_was ()
		self.was.subapp = current_app
		try:
			content = self.generate_content (thing, (), param)
		except:				
			self.rollback ()
			content = request.response ("500 Internal Server Error", exc_info = self.was.app.debug and sys.exc_info () or None)
		else:
			self.commit ()
		
		# clean was
		del self.was.env
		del self.was.subapp
		return content
		