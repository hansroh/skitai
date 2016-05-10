from . import mbox, session

class NamedSession:
	def __init__ (self, wclass, cookie, request, securekey, timeout = 1200):
		self.__wclass = wclass
		self.__cookie = cookie
		self.__obj = None
		self.__request = request
		self.__securekey = securekey		
		self.__timeout = timeout
	
	def mount (self, name = None, securekey = None, path = None, domain = None, secure = False, http_only = False, session_timeout = None):		
		if self.__obj:
			self.__obj.commit ()
								
		securekey, session_timeout = self.__get_config (securekey, session_timeout)
		if not securekey:
			raise AssertionError ("Secret key is not configuured")
		
		if not name:
			if not (path is None or path == "/"):
				raise AssertionError ("No-Nameed session path should be None or '/'")
			name = ""
			path = "/"
		else:
			name = "_" + name.upper ()
		
		if self.__wclass == "session":
			obj = self.__get_session (name, securekey, session_timeout)
		else:
			if session_timeout:
				raise AssertionError ("Cannot set timeout for mbox")
			obj = self.__get_notices (name, securekey)
			
		obj.config (path, domain, secure, http_only)
		self.__obj = obj
	
	def exists (self, name = None):
		if name is None:
			name = ""
		return name in self.__dataset
		
	def __getattr__ (self, attr):
		if self.__obj is None:
			self.mount ()
		return getattr (self.__obj, attr)
	
	def __get_config (self, securekey, session_timeout):	
		return (
		 securekey and securekey.encode ("utf8") or self.__securekey,
		 session_timeout and session_timeout or self.__timeout
		)
		
	def __get_session (self, name, securekey, session_timeout):			
		return session.Session (name, self.__cookie, self.__request, securekey, session_timeout)
			
	def __get_notices (self, name, securekey):		
		return mbox.MessageBox (name, self.__cookie, self.__request, securekey)

	