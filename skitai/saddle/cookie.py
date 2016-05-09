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
from . import named_session

def crack_cookie (r):
	if not r: return {}
	arg={}
	q = [x.split('=', 1) for x in r.split('; ')]	
	for k in q:
		key = unquote_plus (k [0])
		if len (k) == 2:			
			if not key.startswith ("SESSION") and not key.startswith ("NOTIS"):
				arg[key] = unquote_plus (k[1])
			else:
				arg[key] = k[1]
		else:
			arg[key] = ""
	return arg


class Cookie:
	ACENTURY = 3153600000
	def __init__ (self, request, securekey = None, default_path = None, session_timeout = 1200):
		self.request = request		
		self.securekey = securekey
		if securekey:
			self.securekey = securekey.encode ("utf8")
		self.default_path = default_path
		self.session_timeout = session_timeout
		self.dirty = False		
		self.data = {}
		self.config = None
		self.uncommits = {}
		self.session_cookie = {}
		self.notices_cookie = {}
		self._parse ()
	
	def __setitem__ (self, k, v):
		self.set (k, v)
		
	def __getitem__ (self, k):
		return self.data [k]
	
	def __delitem__ (self, k):
		return self.remove (k)
	
	def __contains__ (self, k):
		return k in self.data
	
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
		
	def get (self, k, a = None):
		return self.data.get (k, a)
	
	def remove (self, k, path = None, domain = None):
		try:
			del self.data [k]
		except KeyError:
			pass
		else:		
			self.set (k, "", 0, path, domain)
		
	def clear (self, path = None, domain = None):
		for k, v in list(self.data.items ()):			
			if k.startswith ("SESSION") or k.startswith ("NOTIS"):
				continue							
			self.set (k, "", 0, path, domain)
		self.data = {}

	@classmethod
	def set_securekey (cls, securekey):	
		cls.securekey = securekey.encode ("utf8")
		
	def _parse (self):
		cookie = crack_cookie (self.request.get_header ("cookie"))
		for k, v in list(cookie.items ()):
			if k.startswith ("SESSION"):
				self.session_cookie [k [7:]] = v					
				continue
			elif k.startswith ("NOTIS"):
				self.notices_cookie [k [5:]] = v
				continue
			self.data [k] = v
	
	def rollback (self):
		self.dirty = False
		
	def commit (self):
		if not self.dirty:
			return			
		for cs in list(self.uncommits.values ()):
			self.request.response ["Set-Cookie"] = cs		
		self.dirty = False
		
	def set (self, name, val = "", expires = None, path = None, domain = None, secure = False, http_only = False):		
		self.dirty = True
		if path is None:
			path = self.default_path
		
		# browser string cookie
		cl = []
		if expires is not None:
			if expires == "never":
				expires = self.ACENTURY
			elif expires == "now":
				expires = 0

		if expires == 0:
			cl = ["%s=%s" % (name, "")]
			cl.append ("path=%s" % path)
		else:
			if name.startswith ("SESSION") or name.startswith ("NOTIS"):
				cl.append ("%s=%s" % (name, val))
			else:
				cl.append ("%s=%s" % (quote_plus (name), quote_plus (val)))
			cl.append ("path=%s" % path)		
		
		if expires is not None:
			cl.append ("expires=%s" % http_date.build_http_date (time.time () + expires))	
			
		if domain:
			cl.append ("domain=%s" % domain)			
		
		if secure:
			cl.append ("Secure")			
		
		if http_only:
			cl.append ("HttpOnly")
			
		self.uncommits [name] = "; ".join (cl)
		
		# cookie data
		if expires == 0:
			try: del self.data [name]
			except KeyError: pass										
		elif not name.startswith ("SESSION") and not name.startswith ("NOTIS"):
			self.data [name] = val
		
	def get_session (self):	
		return named_session.NamedSession ("session", self.session_cookie, self.request, self.securekey, self.set, self.session_timeout)	
		
	def get_notices (self):
		return named_session.NamedSession ("mbox", self.notices_cookie, self.request, self.securekey, self.set, self.session_timeout)
		

