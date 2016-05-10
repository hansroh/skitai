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


class BasicMethods:
	def __setitem__ (self, k, v):
		self.set (k, v)
		
	def __getitem__ (self, k):
		return self.get (k)
	
	def __delitem__ (self, k):
		return self.remove (k)
	
	def __contains__ (self, k):
		self.data is None and self.__parse ()
		return k in self.data
	
	def iterkeys (self):		
		self.data is None and self.__parse ()
		return self.data.iterkeys ()
	
	def itervalues (self):		
		self.data is None and self.__parse ()
		return self.data.itervalues ()	
	
	def iteritems (self):		
		self.data is None and self.__parse ()
		return self.data.iteritems ()	
		
	def has_key (self, k):
		self.data is None and self.__parse ()
		return k in self.data
	
	def items (self):
		self.data is None and self.__parse ()
		return list(self.data.items ())
	
	def keys (self):
		self.data is None and self.__parse ()
		return list(self.data.keys ())	
	
	def values (self):
		self.data is None and self.__parse ()
		return list(self.data.values ())	
		

class Cookie (BasicMethods):
	ACENTURY = 3153600000
	
	def __init__ (self, request, securekey = None, default_path = None, session_timeout = 1200):
		self.request = request		
		if securekey:
			self.securekey = securekey.encode ("utf8")
		else:
			self.securekey = securekey				
		self.default_path = default_path
		self.session_timeout = session_timeout
		self.dirty = False		
		self.data = None
		self.uncommits = {}
		self.sessions = {}		
	
	def __parse (self):
		self.data = {}	
		cookie = crack_cookie (self.request.get_header ("cookie"))
		for k, v in list(cookie.items ()):
			if k.startswith ("SESSION") or k.startswith ("NOTIS"):
				self.sessions [k] = v					
				continue			
			self.data [k] = v
		
	def get (self, k, a = None):
		self.data is None and self.__parse ()
		return self.data.get (k, a)
	
	def remove (self, k, path = None, domain = None):
		self.data is None and self.__parse ()
		try:
			del self.data [k]
		except KeyError:
			pass
		else:		
			self.set (k, "", 0, path, domain)
	
	def clear (self, path = None, domain = None):
		self.data is None and self.__parse ()
		for k, v in list(self.data.items ()):			
			self.set (k, "", 0, path, domain)
		self.data = {}
	
	def rollback (self):
		self.dirty = False		
		
	def commit (self):
		if self.data is None or not self.dirty:
			return			
		for cs in list(self.uncommits.values ()):
			self.request.response ["Set-Cookie"] = cs		
		self.dirty = False
		
	def set (self, name, val = "", expires = None, path = None, domain = None, secure = False, http_only = False):
		self.data is None and self.__parse ()
						
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
	
	def get_named_session_data (self, name):
		self.data is None and self.__parse ()
		return self.sessions.get (name)
				
	def get_session (self):
		return named_session.NamedSession ("session", self, self.request, self.securekey, self.session_timeout)
		
	def get_notices (self):
		return  named_session.NamedSession ("mbox", self, self.request, self.securekey, self.session_timeout)
		

