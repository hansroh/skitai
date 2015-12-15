import base64
from hashlib import md5

class Authorizer:
	def __init__ (self, realm, apikey, password):
		self.realm = realm
		self.apikey = apikey.encode ("utf8")
		self.md5_apikey = md5 (self.apikey).hexdigest ()
		self.password = password
		self.cache = {}
	
	def get_authority (self, authkey, request = None):
		authinfo = request.get_header (authkey)		
		if not authinfo: return None
		
		if authinfo in self.cache:
			return self.cache [authinfo]
		
		basic = base64.decodestring (authinfo [6:])
		if basic == self.md5_apikey:
			self.cache [authinfo] = "app"
			return "app"
		
		username, password = basic.split (":")				
		if username != "admin": 
			return None
		
		try:
			assert (password == self.password)
		except AssertionError:
			return None
		else:
			self.cache [authinfo] = "admin"
			return "admin"
	
	def _has_permission (self, group, permission):
		if not permission:
			return True #all
		if group == "admin":
			return True
		else:
			return group in permission
					
	def has_permission (self, request, permission = None, push_error = 1):
		group = self.get_authority ('Authorization', request)
		if group is None:
			request.response ['WWW-Authenticate'] = 'Basic realm="%s Secured"' % self.realm
			if push_error:
				request.response.error (401)
			return False
		if not self._has_permission (group, permission):
			if push_error: 
				request.response.error (403, "", "You haven't permission for accessing this page")
			return False
		return True


class FileAuthorizer (Authorizer):
	cache = {}
	def __init__ (self, realm, apikey):
		self.realm = realm
		self.apikey = apikey
		self.md5_apikey = md5.new (self.apikey).hexdigest ()
		self.userfile = None
		self.users = {}		
		
	def register (self, username, image, group):
		self.users [username] = (image, group)		
	
	def load (self, userfile):
		f = open (userfile, 'r')
		for line in f:
			line = line.strip ()
			if not line: break
			username, group, image = line.split (":")				
			self.register (username, image, group)						
		f.close ()
		self.userfile = userfile
		
	def digest (self, username, group, password):
		return md5.new ("%s:%s:%s" % (username, group, password)).hexdigest ()
		
	def useradd (self, username, password, group):
		self.register (username, self.digest (username, group, password), group)
		self.save ()
		return True
		
	def usermod (self, username, password, group):
		self.useradd (username, password, group)
		self.save ()
		return True
		
	def userdel (self, username):
		try:
			del self.users [username]
		except KeyError:
			return True	
		self.save ()
		return True
	
	def isvaliduser (self, username, password):
		return self.digest (username, password) == self.users [username][0]
			
	def save (self, fn = None):
		f = open (self.userfile, "w")
		for username, (image, grp) in list(self.users.items ()):
			f.write ("%s:%s:%s\n" % (username, grp, image))
		f.close ()
			
	def get_authority (self, authkey, request = None):
		authinfo = request.get_header (authkey)		
		if not authinfo: return None
		
		if authinfo in self.cache:
			return self.cache [authinfo]
		
		basic = base64.decodestring (authinfo [6:])
		if basic == self.md5_apikey:
			return "app"
		
		username, password = basic.split (":")				
		try:
			group = self.users [username][1]
		except KeyError:
			return None

		image = self.digest (username, group, password)		
		try:
			assert (image == self.users [username][0])
		except AssertionError:
			return None
		else:
			self.cache [authinfo] = group
			return group
	
	def get_userinfo (self, authkey, request = None):	
		authinfo = request.get_header (authkey)		
		if not authinfo: return None
		
		basic = base64.decodestring (authinfo [6:])
		if basic == self.md5_apikey:
			return None, "app"
		
		username, password = basic.split (":")				
		group = self.users [username][1]
		return username, group
		
		