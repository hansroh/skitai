from aquests.protocols.http import http_util
from . import cookie
from aquests.lib.reraise import reraise 
import sys
import json
from aquests.lib.athreads import trigger
from aquests.lib.attrdict import AttrDict
from aquests.protocols.http import respcodes
from skitai.saddle.exceptions import HTTPError

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
				if response is not None:
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
			exc_info = sys.exc_info ()
			self.was.subapp.emit ("request:failed", exc_info)
			if failed:				
				response = failed (self.was, exc_info)
			if response is None:
				raise
			else:
				# filed handle exception and contents, just log
				self.was.traceback ()
							
		else:
			self.was.subapp.emit ("request:success")
			success and success (self.was)
		
		self.was.subapp.emit ("request:teardown")
		teardown and teardown (self.was)
		return response
		
	def generate_content (self, method, _args, karg):
		karg = self.parse_kargs (karg)
		response = self.chained_exec (method, _args, karg)
		return response
	
	def is_call_args_group (self, data, forward = True):
		if self.was.request.routable.get ('keywords'):
			return True
		wanted_args = self.was.request.routable.get ('args') [self.was.request.routable.get ('urlargs', 0):]
		
		if not wanted_args:
			return False
			
		if forward:
			if wanted_args:
				return True
			for k in wanted_args:
				if k in data:
					return True
		
		else:		
			for i in range (-1, -(len (wanted_args) + 1), -1):
				if wanted_args [i] in data:
					return True
					
		return False
				
	def parse_kargs (self, kargs):
		query = self.env.get ("QUERY_STRING")
		data = self.was.request.dict () or self.env.get ("wsgi.input")
		
		allkarg = AttrDict ()		
		self.merge_args (allkarg, kargs)
		
		if not query and not data:
			self.was.request.set_args (allkarg)
			return kargs
		
		query_included = True
		if query: 
			querydict = http_util.crack_query (query)
			self.merge_args (allkarg, querydict)
			if self.is_call_args_group (querydict):				
				if not data:		
					self.was.request.set_args (allkarg)
					return allkarg				
				self.merge_args (kargs, querydict)
			else:
				query_included = False
		
		if data:
			self.merge_args (allkarg, data, overwrite = True)
			if query_included and self.is_call_args_group (data, False):
				self.was.request.set_args (allkarg)
				return allkarg
			
		self.was.request.set_args (allkarg)
		return kargs
		
	def merge_args (self, s, n, overwrite = False):
		for k, v in list(n.items ()):
			if k in s:
				if overwrite:
					s [k] = v
					continue
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
		if self.was.app is None:
			# this is failed request
			return
		# keep commit order, session -> mbox -> cookie
		if hasattr (self.was.request, "django"):
			self.was.request.django.commit ()
		if not self.was.in__dict__ ("cookie"):
			return		
		if self.was.in__dict__ ("session"):
			self.was.session and self.was.session.commit ()
		if self.was.in__dict__ ("mbox"):
			self.was.mbox and self.was.mbox.commit ()			
		self.was.cookie.commit ()
	
	def rollback (self):
		if self.was.app is None:
			# this is failed request
			return		
		if not self.was.in__dict__ ("cookie"):		
			return			
		# keep commit order, session -> mbox -> cookie
		if self.was.in__dict__ ("session"):		
			self.was.session and self.was.session.rollback ()
		if self.was.in__dict__ ("mbox"):
			self.was.mbox and self.was.mbox.rollback ()
		self.was.cookie.rollback ()
	
	def find_method (self, request, path, handle_response = True):
		current_app, thing, param, options, respcode = self.get_method (
			path, 
			request
		)
		
		if respcode and handle_response:			
			if respcode == 301:
				request.response ["Location"] = thing
				request.response.error (301, "Object Moved", why = 'Object Moved To <a href="%s">Here</a>' % thing)							
			elif respcode != 200:
				request.response.error (respcode, respcodes.get (respcode, "Undefined Error"))

		if thing:
			request.routed = current_app.get_routed (thing)
			request.routable = options

		return current_app, thing, param, respcode
		
	def __call__ (self):
		request = self.env ["skitai.was"].request
		current_app, thing, param, respcode = self.find_method (request, self.env ["PATH_INFO"])
		
		if respcode: 
			# unacceptable
			return b""
		
		current_app.emit ("request:started")
		self.build_was ()
		self.was.subapp = current_app
		
		try:
			content = self.generate_content (thing, (), param)
		except HTTPError as e:
			content = request.response.with_explain (e.status, e.explain)
		except:
			self.rollback ()
			if request.response.is_responsable ():
				content = request.response ("500 Internal Server Error", exc_info = self.was.app.debug and sys.exc_info () or None)
			del self.was.env
			del self.was.subapp
			raise
		
		self.commit ()
		# clean was		
		del self.was.env
		del self.was.subapp
		current_app.emit ("request:finished")
		return content
		