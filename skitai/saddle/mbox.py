from .secured_cookie_value import SecuredListValue
import time

class MessageBox (SecuredListValue):
	KEY = "NOTIS"
	
	def __init__ (self, name, cookie, request, secret_key):
		SecuredListValue.__init__ (self, name, cookie, request, secret_key)
		self.mid = -1
	
	def serialize (self):
		self.data.append ((-1, time.time (), self.request.get_remote_addr ())) # add random string
		return SecuredListValue.serialize (self)
		
	def validate (self):	
		if not self.data:
			self.data = []
			return
			
		if self.data and self.data [0][0] != -1:
			return
			
		validator, self.data = self.data [0], self.data [1:]
		last_update, addr = validator [1:3]
		self.__source_verified = (addr == self.request.get_remote_addr ())
					
	def send (self, msg, category = "info", valid = 0, **extra):
		self.data is None and self.unserialize ()
		if self.data and self.mid == -1:
			self.mid = max ([n [0] for n in self.data])		
		self.mid += 1
		self.data.append ((self.mid, category, int (time.time ()), valid, msg, extra))
		self.dirty = True
		
	def remove (self, mid):
		self.data is None and self.unserialize ()
		index = 0
		found = False
		for n in self.data:
			if n [0] == mid:
				found = True
				break
			index += 1
		if found:
			self.data.pop (index)
		self.dirty = True
	
	def search (self, k, v = None):
		self.data is None and self.unserialize ()
		mids = []
		for notice in self.data:
			if v is None:
				if notice [1] == k:
					mids.append (notice [0])
			elif notice [5].get (k) == v:
				mids.append (notice [0])
		return mids
	
	def getv (self, k = None, v = None):
		if not self.__source_verified:
			self.data = []
			self.dirty = True
			return []
		return self.get (k, v)	
		
	def get (self, k = None, v = None):
		self.data is None and self.unserialize ()
		mids = []
		if k:
			mids = self.search (k, v)

		now = int (time.time ())
		messages = []
		not_expired = []
		
		for notice in self.data:
			how_old = now - notice [2]			
			if notice [3] and how_old > notice [3]:
				# expired, drop
				continue
				
			if mids and notice [0] not in mids:
				not_expired.append (notice)
				continue
				
			if notice [3]:
				not_expired.append (notice)			
							
			messages.append (notice)
		
		if len (self.data) != len (not_expired):
			self.data = not_expired
			self.dirty = True
			
		return messages
	
	def recal_expires (self, expires):						
		if self.data:
			return "never"
		return 0
	

