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
from . import secured_cookie_value

def crack_cookie (r):
	if not r: return {}
	arg={}
	q = [x.split('=', 1) for x in r.split('; ')]	
	for k in q:
		key = unquote_plus (k [0])
		if len (k) == 2:			
			if key not in ("SESSION", "NOTIS"):
				arg[key] = unquote_plus (k[1])
			else:
				arg[key] = k[1]	
		else:
			arg[key] = ""
	return arg


class Cookie:
	ACENTURY = 3153600000
	def __init__ (self, request, secret_key = None, session_timeout = 1200):
		self.request = request		
		self.secret_key = secret_key
		if secret_key:
			self.secret_key = secret_key.encode ("utf8")
		self.session_timeout = session_timeout
		self.dirty = False		
		self.data = {}
		self.uncommits = {}
		self.session_cookie = None
		self.notices_cookie = None
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
	
	def remove (self, k):
		try:
			del self.data [k]
		except KeyError:
			pass
		else:		
			self.set (k, expires = 0)
		
	def clear (self):
		for k, v in list(self.data.items ()):			
			if k in ("SESSION", "NOTIS"): 
				continue
			self.set (k, expires = 0)
		self.data = {}	
			
	@classmethod
	def set_secret_key (cls, secret_key):	
		cls.secret_key = secret_key.encode ("utf8")
		
	def _parse (self):
		cookie = crack_cookie (self.request.get_header ("cookie"))			
		for k, v in list(cookie.items ()):
			if k == "SESSION":
				self.session_cookie = v
				continue
			if k == "NOTIS":
				self.notices_cookie = v
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
			
	def set (self, name, val = "", expires = None, path = "/", domain = None):
		self.dirty = True
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
			if name in ("SESSION", "NOTIS"):
				cl.append ("%s=%s" % (name, val))
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
		elif name not in ("SESSION", "NOTIS"):
			self.data [name] = val
		
	def get_session (self, create = True):
		if self.secret_key:
			if self.session_cookie:
				sc = secured_cookie_value.Session.unserialize (self.request, self.session_cookie.encode ("utf8"), self.secret_key, self.set, self.session_timeout)
				self.session_cookie = None
				return sc
			elif create:
				return secured_cookie_value.Session (self.request, None, self.secret_key, self.set, True, self.session_timeout)
		return None
	
	def get_notices (self, create = True):
		if self.secret_key:
			if self.notices_cookie:
				sc = secured_cookie_value.MessageBox.unserialize (self.request, self.notices_cookie.encode ("utf8"), self.secret_key, self.set)
				self.notices_cookie = None
				return sc
			elif create:
				return secured_cookie_value.MessageBox (self.request, None, self.secret_key, self.set, True)
		return None
		

