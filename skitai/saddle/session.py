from .secured_cookie_value import SecuredDictValue
import time

class Session (SecuredDictValue):
	default_session_timeout = 1200 # 20 min.	
	KEY = "SESSION"	
	
	def __init__ (self, name, cookie, request, secret_key, session_timeout = 0):
		self.session_timeout = session_timeout and session_timeout or self.default_session_timeout
		SecuredDictValue.__init__ (self, name, cookie, request, secret_key)
			
	def validate (self):
		if not '_expires' in self.data:
			self.data = {}
			return
			
		if type (self.data ['_expires']) is tuple:
			expires, addr = self.data ['_expires']
			self.__source_verified = (addr == self.request.get_remote_addr ())				
		else:
			expires = self.data ['_expires']
			
		if time.time() > expires: # expired
			self.data = {}
			return
			
		if self.session_timeout + time.time () < expires: # too long, maybe fraud
			self.data = {}
			return
	
	def getv (self, k, v = None):
		if not self.__source_verified:			
			self.data = {}
			self.dirty = True
			return v
		return self.get (k, v)
				
	def recal_expires (self, expires):
		if expires is None:
			return self.session_timeout
		if expires == "now":
			return 0
		if expires == "never":
			raise ValueError("session must be specified expires seconds")
		return int (expires)
		
	def commit (self, expires = None):
		# always commit for extending/expiring expires
		if not self.dirty or self.data is None: return
		expires = self.recal_expires (expires)
		self ["_expires"] = (time.time () + expires, self.request.get_remote_addr ())
		if len (self.data) == 1: # only have _expires, expire now
			expires = 0
		self.set_cookie (expires)		
		
	def set_default_session_timeout (self, timeout):
		self.default_session_timeout = timeout

