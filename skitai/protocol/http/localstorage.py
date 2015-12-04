import base64
import random
try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse	
from . import util

localstorage = None

def create (logger):
	global localstorage
	localstorage = LocalStorage (logger)


class LocalStorage:
	def __init__ (self, logger):
		self.logger = logger
		self.cookie = {}
		self.data = {}
		self.cookie_protected = {}
	
	def get_host (self, url):
		return urlparse (url) [1].split (":") [0]
	
	def set_item (self, url, key, val):
		host = self.get_host (url)
		if host not in self.data:
			self.data = {}
		self.data [key] = val
	
	def get_item (self, url, key):
		host = self.get_host (url)
		try:
			return self.data [host][key]
		except KeyError:
			return 
				
	def set_protect_cookie (self, url, name, flag = 1):
		host = self.get_host (url)
		try:
			self.cookie_protected [host][name] = flag
		except KeyError:
			self.cookie_protected [host] = {}	
			self.cookie_protected [host][name] = flag
	
	def is_protected_cookie (self, url, name):
		host = self.get_host (url)
		try:
			protected = self.cookie_protected [host][name]
		except KeyError:
			return False
		return protected		
			
	def get_cookie (self, url):
		url = url.lower ()
		cookie = []
		for domain in self.cookie:
			host = self.get_host (url)
			if ("." + host).find (domain) > -1:
				for path in self.cookie [domain]:
					if script.find (path) > -1:
						cookie += list(self.cookie [domain][path].items ())
		return cookie
	
	def get_cookie_string (self, url):	
		cookie = self.get_cookie (url)
		if cookie:
			return "; ".join (["%s=%s" % (x, y) for x, y in cookie])			
		return ""
	
	def get_cookie_dict (self, url):	
		cookie = self.get_cookie (url)
		dict = {}
		if cookie:
			for k, v in cookie:
				dict [k] = v		
		return dict
		
	def set_default_cookie (self, url, cookie):
		host = self.get_host (url)
		self.cookie [host] = {}
		self.cookie [host]["/"] = {}
		
		if type (cookie) != type ([]):
			cookie = util.strdecode (cookie, 1)
					
		for k, v in cookie:
			self.cookie [host]["/"][k] = v
	
	def clear_cookie (self, url):
		url = url.lower ()
		for domain in list(self.cookie.keys ()):
			if url.find (domain) > -1:
				del self.cookie [domain]				
		
	def set_cookie (self, url, cookiestr):
		host = self.get_host (url)
		ckey, cval = '', ''				
		s = {}
		count = 0
		for element in cookiestr.split (";"):
			try: 
				k, v = element.split ("=", 1)
			except:
				k, v = element, ''
			
			if v:
				_cookie = self.get_cookie_dict (url)
				if k in _cookie:					
					if self.is_protected_cookie (url, k): return					
			
			if count == 0:			
				if v.find ("%") != -1:
					ckey, cval = k.strip (), v.strip ()
				else:
					ckey, cval = k.strip (), v.strip ()
			else:
				s [k.strip ().lower ()] = v.strip ().lower ()
				
			count += 1
		
		try: domain = s ['domain']
		except KeyError: domain = host
		try: path = s ['path']
		except KeyError: path = '/'
		
		try: self.cookie [domain]
		except KeyError: self.cookie [domain] = {}
		try: self.cookie [domain][path]
		except KeyError: self.cookie [domain][path] = {}
					
		self.cookie [domain][path][ckey] = cval			
