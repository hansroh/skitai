import pickle as pickle
from . import http_date
import time
import random
from skitai.lib import pathtool
from skitai.lib import udict
import os, sys
try:
	from urllib.parse import quote_plus, unquote_plus
except ImportError:
	from urllib import quote_plus, unquote_plus	
import base64

def crack_cookie (r):
	if not r: return {}
	arg={}
	q = [x.split('=', 1) for x in r.split('; ')]	
	for k in q:
		key = unquote_plus (k [0])
		if len (k) == 2:			
			if key != "SESSION":
				arg[key] = unquote_plus (k[1])
			else:
				arg[key] = k[1]	
		else:
			arg[key] = ""
	return arg


class Cookie:
	DOUBLEDECADE = 630720000
	secret_key = None
	def __init__ (self, request):
		self.request = request		
		self.data = {}
		self.uncommits = {}
		self.session_cookie = None
		self._parse ()
	
	def __setitem__ (self, k, v):
		self.set (k, v)
		
	def __getitem__ (self, k):
		return self.data [k]
	
	def __delitem__ (self, k):
		return self.remove (k)
		
	def has_key (self, k):
		return k in self.data
	
	def items (self):
		return list(self.data.items ())
	
	def keys (self):
		return list(self.data.keys ())	
	
	def get (self, k, a = None):
		return self.data.get (k, a)
		
	def values (self):
		return list(self.data.values ())	
	
	def remove (self, k):
		try:
			del self.data [k]
		except KeyError:
			pass
		else:		
			self.set (k, expires = 0)	
		
	def clear (self):
		for k, v in list(self.data.items ()):			
			if k == "SESSION": 
				continue
			self.set (k, expires = 0)
		self.data = {}	
			
	@classmethod
	def set_secret_key (cls, secret_key):	
		cls.secret_key = secret_key.encode ("utf8")
	
	def get_session (self, create = True):
		if self.session_cookie:
				sc = SecuredCookieValue.unserialize (self.session_cookie.encode ("utf8"), self.secret_key, self.set)
				self.session_cookie = None
				return sc
		elif create:
			return SecuredCookieValue (None, self.secret_key, self.set, True)
		raise KeyError("no session found")
	
	def _parse (self):
		cookie = crack_cookie (self.request.get_header ("cookie"))			
		for k, v in list(cookie.items ()):
			if k == "SESSION":
				self.session_cookie = v
				continue
			self.data [k] = v
	
	def commit (self):
		for cs in list(self.uncommits.values ()):
			self.request.response ["Set-Cookie"] = cs
			
	def set (self, name, val = "", expires = None, path = "/", domain = None):
		# browser string cookie
		cl = []
		if expires is not None:
			if expires == "never":
				expires = self.DOUBLEDECADE
			elif expires == "now":
				expires = 0		
			
		if expires == 0:
			cl = ["%s=%s" % (name, "")]
			cl.append ("path=%s" % path)
		else:
			if name == "SESSION":
				cl.append ("%s=%s" % ("SESSION", val))
			else:
				cl.append ("%s=%s" % (quote_plus (name), quote_plus (val)))
			cl.append ("path=%s" % path)		
		
		if expires is not None:
			cl.append ("expires=%s" % http_date.build_http_date (time.time () + expires))	
			
		if domain:
			cl.append ("domain=%s" % domain)			
		
		self.uncommits [name] = "; ".join (cl)
		
		# cookie data
		if expires == 0:
			try: del self.data [name]
			except KeyError: pass										
		elif name != "SESSION":
			self.data [name] = val
	

_default_hash = None
if sys.version_info >= (2, 5):
	try:
		from hashlib import sha1 as _default_hash
	except ImportError:
		pass
if _default_hash is None:
	import sha as _default_hash
	
import pickle as pickle
from hmac import new as hmac

class UnquoteError(Exception):
	"""Internal exception used to signal failures on quoting."""


class SecuredCookieValue (Cookie):
	hash_method = _default_hash
	serialization_method = pickle
	quote_base64 = True	
	default_session_timeout = 1200 # 20 min.
	max_valid_session = 7200 # 2hours
		
	def __init__ (self, data, secret_key, setfunc, new = True):
		if new:
			self.data = {}
		else:
			self.data = data				
		self.secret_key = secret_key
		self.setfunc = setfunc
		self.new = new
		self.commited = False
		
	def __setitem__ (self, k, v):		
		self.set (k, v)
	
	def __delitem__ (self, k):
		return self.remove (k)
	
	def remove (self, k):
		try:
			del self.data [k]
		except KeyError:
			pass
			
	def set (self, k, v):
		if type (k) is not type (""):
			raise TypeError("Session key must be string type")
		self.data [k] = v
		
	def clear (self):
		self.data = {}
	
	def commit (self, expires = None, path = "/", domain = None):
		if self.commited:
			return			
						
		if expires is None:
			expires = self.default_session_timeout
		elif expires == "now":
			expires = 0
		elif expires == "never":
			raise ValueError("session must be specified expires seconds")
		else:
			expires = min (int (expires), self.max_valid_session)
		
		self ["_expires"] = time.time () + expires
		self.setfunc ("SESSION", self.serialize (), expires, path, domain)
		self.commited = True
		
	def set_default_session_timeout (self, timeout):
		self.default_session_timeout = timeout
		
	@classmethod
	def quote (cls, value):		
		if cls.serialization_method is not None:
			value = cls.serialization_method.dumps(value)			
		if cls.quote_base64:
			value = base64.b64encode (value)
			value = b''.join(value.splitlines()).strip()
		return value
	
	@classmethod
	def unquote(cls, value):
		try:
			if cls.quote_base64:
				value = base64.b64decode(value)
			if cls.serialization_method is not None:
				value = cls.serialization_method.loads(value)
			return value
		except:			
			raise UnquoteError()

	def serialize(self):
		if self.secret_key is None:
			raise RuntimeError('no secret key defined')
		
		result = []
		mac = hmac(self.secret_key, None, self.hash_method)
		for key, value in sorted (self.items(), key = lambda x: x[0]):
			result.append (quote_plus (key).encode ("utf8") + b"=" + self.quote(value))
			mac.update(b'|' + result[-1])			
		return (base64.b64encode(mac.digest()).strip() + b"?" + b'&'.join(result)).decode ("utf8")
	
	@classmethod
	def unserialize(cls, string, secret_key, setfunc):
		items = {}
		try:
			base64_hash, data = string.split(b'?', 1)
		except:
			base64_hash, data, items = b"", b"", None
		
		mac = hmac(secret_key, None, cls.hash_method)
		for item in data.split(b'&'):
			mac.update(b'|' + item)
			if not b'=' in item:
				items = None
				break
			key, value = item.split(b'=', 1)
			# try to make the key a string
			try:
				key = unquote_plus (key.decode ("utf8"))
			except UnicodeError:
				pass
			items[key] = value
		
		try:
			client_hash = base64.b64decode(base64_hash)
		except Exception:
			items = client_hash = None
		
		if items is not None and client_hash == mac.digest():
			try:
				for key, value in items.items():					
					items[key] = cls.unquote(value)
			except UnquoteError:
				items = {}
			else:
				if '_expires' in items:
					if time.time() > items['_expires']: # expired
						items = {}
					if cls.max_valid_session + time.time () < items['_expires']: # too long, maybe fraud
						items = {}
				else:							
					items = {} # no expires? maybe fraud
		else:
			items = {}
						
		return cls (items, secret_key, setfunc, False)

		