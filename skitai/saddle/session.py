from .secured_cookie_value import SecuredDictValue
import time

class Session (SecuredDictValue):
	default_session_timeout = 1200 # 20 min.	
	KEY = "sdlsess"
	VALIDS = "_valids"
	
	def __init__ (self, name, cookie, request, secret_key, session_timeout = 0):
		self.session_timeout = session_timeout and session_timeout or self.default_session_timeout
		self.new_session_timeout = None
		SecuredDictValue.__init__ (self, name, cookie, request, secret_key)
	
	def _recal_expires (self, expires):
		if expires is None:
			if self.new_session_timeout is not None:
				expires = self.new_session_timeout			
			else:
				return self.session_timeout
		if expires == "now":
			return 0
		if expires == "never":
			raise ValueError("session must be specified expires seconds")
		return int (expires)
			
	def validate (self):
		if self.VALIDS not in self.data:
			self.data = {}
			return
			
		if type (self.data [self.VALIDS]) is tuple:
			expires, addr = self.data [self.VALIDS]
			self._source_verified = (addr == self.request.get_remote_addr ())				
		else:
			expires = self.data [self.VALIDS]
			
		if time.time() > expires: # expired
			self.data = {}
			return
			
		if self.session_timeout + time.time () < expires: # too long, maybe fraud
			self.data = {}
			return
	
	def getv (self, k, v = None):
		if not self._source_verified:
			self.data = {}
			self.dirty = True
			return v
		return self.get (k, v)
	
	def touch (self):
		self.dirty = True
	
	def set_expiry (self, timeout):		
		self.new_session_timeout = timeout
		self.dirty = True
	
	def get_expiry (self):		
		if not self.data.get (self.VALIDS):
			return
		return self.data [self.VALIDS][0]
		
	def expire (self):
		self.clear ()
		self.new_session_timeout = 'now'
	
	def commit (self, expires = None):
		if not self.dirty or self.data is None: 
			return
		
		if len (self.data) == 1 and self.VALIDS in self.data: # only have _expires, expire now
			expires = 0
		else:	
			expires = self._recal_expires (expires)
		
		if not expires:
			self [self.VALIDS] = (time.time (), self.request.get_remote_addr ())
			
		else:	
			new = time.time () + expires
			if "_expire" not in self.data:
				self [self.VALIDS] = (new, self.request.get_remote_addr ())
			else:	
				current = self [self.VALIDS][0]				
				if self.new_session_timeout or new > current:
					#already set_expiry
					self [self.VALIDS] = (new, self.request.get_remote_addr ())
				else:
					expires = current - time.time ()
		
		self.set_cookie (expires)
		self.dirty = False
	