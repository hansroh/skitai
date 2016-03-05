import pickle as pickle
from skitai.server import http_date
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
import pickle
from hmac import new as hmac

_default_hash = None
if sys.version_info >= (2, 5):
	try:
		from hashlib import sha1 as _default_hash
	except ImportError:
		pass
if _default_hash is None:
	import sha as _default_hash


class UnquoteError(Exception):
	"""Internal exception used to signal failures on quoting."""


class SecuredValue:
	hash_method = _default_hash
	serialization_method = pickle
	quote_base64 = True
	KEY = "SECURED"	
	
	def __init__ (self, request, data, secret_key, setfunc, new = True):
		self.request = request
		if new:
			self.set_default_data ()
		else:
			self.data = data				
		self.secret_key = secret_key
		self.setfunc = setfunc
		self.new = new
		self.dirty = False
		
	def __contains__ (self, k):
		return k in self.data
		
	def set_default_data (self):
		self.dirty = False
		self.data = None
	
	def clear (self):
		self.set_default_data ()
		
	def recal_expires (self, expires):						
		return expires
	
	def rollback (self):
		self.dirty = False
			
	def commit (self, expires = None, path = "/", domain = None):
		if not self.dirty:
			return
		expires = self.recal_expires (expires)
		self.setfunc (self.KEY, self.serialize (), expires, path, domain)
		self.dirty = False
		
	@classmethod
	def quote (cls, value):		
		if cls.serialization_method is not None:
			value = cls.serialization_method.dumps(value, 1)			
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
			raise UnquoteError


class SecuredDictValue (SecuredValue):
	KEY = "SECUREDICT"	
			
	def set_default_data (self):
		self.dirty = True
		self.data = {}
			
	def __setitem__ (self, k, v):
		self.set (k, v)
	
	def __delitem__ (self, k):
		return self.remove (k)
	
	def __getitem__ (self, k, v = None):
		return self.data.get (k, v)
	
	def iterkeys (self):		
		return self.data.iterkeys ()
	
	def itervalues (self):		
		return self.data.itervalues ()	
	
	def iteritems (self):		
		return self.data.iteritems ()	
		
	def has_key (self, k):
		return k in self.data
	
	def items (self):
		return list(self.data.items ())
	
	def keys (self):
		return list(self.data.keys ())	
	
	def values (self):
		return list(self.data.values ())	
			
	def remove (self, k):
		try:
			del self.data [k]
		except KeyError:
			pass
		else:
			self.dirty = True
			
	def set (self, k, v):
		if type (k) is not type (""):
			raise TypeError("Session key must be string type")
		self.data [k] = v
		self.dirty = True
	
	def get (self, k, v = None):
		return self.data.get (k, v)
		
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
	def unserialize(cls, request, string, secret_key, setfunc, *args, **kargs):
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
			items = {}
						
		return cls (request, items, secret_key, setfunc, False, *args, **kargs)		

class SecuredListValue (SecuredValue):
	KEY = "SECURELIST"	
	
	def set_default_data (self):
		self.dirty = True
		self.data = []
	
	def serialize(self):
		if self.secret_key is None:
			raise RuntimeError('no secret key defined')
								
		result = []
		mac = hmac(self.secret_key, None, self.hash_method)
		for value in sorted (self.data):
			result.append (self.quote (value))
			mac.update(b'|' + result[-1])
		return (base64.b64encode(mac.digest()).strip() + b"?" + b'&'.join(result)).decode ("utf8")
	
	@classmethod
	def unserialize(cls, request, string, secret_key, setfunc, *args, **kargs):
		items = []
		try:
			base64_hash, data = string.split(b'?', 1)
		except:
			base64_hash, data, items = b"", b"", None
		
		mac = hmac(secret_key, None, cls.hash_method)
		for item in data.split(b'&'):
			mac.update(b'|' + item)
			items.append (cls.unquote (item))
		
		try:
			client_hash = base64.b64decode(base64_hash)
		except Exception:
			items = client_hash = None
					
		return cls (request, items, secret_key, setfunc, False, *args, **kargs)
				
			
class Session (SecuredDictValue):
	default_session_timeout = 1200 # 20 min.	
	KEY = "SESSION"	
	
	def __init__ (self, request, data, secret_key, setfunc, new = True, session_timeout = 0):
		SecuredValue.__init__ (self, request, data, secret_key, setfunc, new)
		self.session_timeout = session_timeout and session_timeout or self.default_session_timeout
		self.__source_verified = False
		if self.data:
			self.validate ()
		
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
		if self.__source_verified:
			return self.get (k, v)
		return v	
		
	def source_verified (self):
		return self.__source_verified
				
	def recal_expires (self, expires):
		if expires is None:
			return self.session_timeout
		if expires == "now":
			return 0
		if expires == "never":
			raise ValueError("session must be specified expires seconds")
		return int (expires)
		
	def commit (self, expires = None, path = "/", domain = None):
		# always commit for extending/expiring expires
		expires = self.recal_expires (expires)
		self ["_expires"] = (time.time () + expires, self.request.get_remote_addr ())
		if len (self.data) == 1: # only have _expires, expire now
			expires = 0
		self.setfunc (self.KEY, self.serialize (), expires, path, domain)
		self.dirty = False
		
	def set_default_session_timeout (self, timeout):
		self.default_session_timeout = timeout
		
		
class MessageBox (SecuredListValue):
	KEY = "NOTIS"
	
	def __init__ (self, request, data, secret_key, setfunc, new = True):
		SecuredValue.__init__ (self, request, data, secret_key, setfunc, new)
		self.mid = -1
		
	def send (self, msg, category = "info", valid = 0, **extra):
		if self.data and self.mid == -1:
			self.mid = max ([n [0] for n in self.data])		
		self.mid += 1
		self.data.append ((self.mid, category, int (time.time ()), valid, msg, extra))
		self.dirty = True
	
	def remove (self, mid):
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
			
	def get (self, *wanted_category):
		now = int (time.time ())
		messages = []	
		not_expired = []
		
		for notice in self.data:
			how_old = now - notice [2]
			
			if notice [3] and how_old > notice [3]:
				# expired, drop
				continue
			
			if wanted_category and notice [1] not in wanted_category:
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
	
	