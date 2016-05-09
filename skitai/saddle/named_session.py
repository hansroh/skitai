from . import secured_cookie_value

class NamedSession:
	def __init__ (self, wclass, dataset, request, securekey, setfunc, timeout = 1200):
		self.__wclass = wclass
		self.__dataset = dataset
		self.__obj = None
		self.__request = request
		self.__securekey = securekey
		self.__setfunc = setfunc
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
		
		data = self.__dataset.get (name)
		if self.__wclass == "session":
			obj = self.__get_session (name, data, securekey, session_timeout)
		else:
			if session_timeout:
				raise AssertionError ("Cannot set timeout for mbox")
			obj = self.__get_notices (name, data, securekey)
			
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
		
	def __get_session (self, name, data, securekey, session_timeout):			
		if data:
			return secured_cookie_value.Session.unserialize (name, self.__request, data.encode ("utf8"), securekey, self.__setfunc, session_timeout)			
		return secured_cookie_value.Session (name, self.__request, None, securekey, self.__setfunc, True, session_timeout)
			
	def __get_notices (self, name, data, securekey):		
		if data:
			return secured_cookie_value.MessageBox.unserialize (name, self.__request, data.encode ("utf8"), securekey, self.__setfunc)			
		return secured_cookie_value.MessageBox (name, self.__request, None, securekey, self.__setfunc, True)

	