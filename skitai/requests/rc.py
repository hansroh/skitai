"""
2015. 12. 7 Hans Roh


ResponseContainer
	logger
	
	udata
	
	uinfo
		url
		scheme
		path
		script
		params
		querystring
		fragment
		method
		netloc
		domain
		host
		port
		auth
		rfc
		referer
		page_id
		referer_id
		depth
		moved
			
	request	
		version
		connection
		user_agent
		proxy
		header		
		content_type
		encoding
		body
		
	response
		version
		code
		msg
		connection
		header
		content_type
		charset
		body
	
	set_cookie (self, k, v)
	get_cookie (self, k)
	set_item (self, k, v)
	get_item (self, k)
	advance (self, surl)	
	sleep (self, timeout)
			
"""
has_lxml = True
try:
	from . import treebuilder
	import html5lib
except ImportError:
	has_lxml = False
import math		
import json
import time

try:
	import xmlrpclib
except ImportError:
	import xmlrpc.client as xmlrpclib
from . import localstorage
try:
	from urllib.parse import urljoin
except ImportError:
	from urlparse import urljoin	
	
class RCRequest:
	def __init__ (self, obj):
		self._header_cache = {}
		self.set (obj)
		
	def set (self, handler):	
		self.header = handler.header
		self.uri = handler.uri
		self.version = handler.http_version
		self.proxy = handler.request.el ["http-proxy"]
		self.connection = handler.request.el ["http-connection"]
		self.user_agent = handler.request.el ["http-user-agent"]
		
		self.body = handler.request.get_data ()
		self.content_type = handler.request.get_content_type ()
		self.encoding = handler.request.encoding
	
	def get_header_with_attr (self, header, default = None):
		d = {}
		v = self.get_header (header)
		if v is None:
			return default, d
			
		v2 = v.split (";")
		if len (v2) == 1:
			return v, d
		for each in v2 [1:]:
			try:
				a, b = each.strip ().split ("=", 1)
			except ValueError:
				a, b = each.strip (), None
			d [a] = b
		return v2 [0], d	
			
	def get_header (self, header, default = None):
		header = header.lower()
		hc = self._header_cache
		if header not in hc:
			h = header + ':'
			hl = len(h)
			for line in self.header:
				if line [:hl].lower() == h:
					r = line [hl:].strip ()
					hc [header] = r
					return r
			hc [header] = None
			return default
		else:
			return hc[header] is not None and hc[header] or default

class RCResponse (RCRequest):
	def set (self, handler):	
		r = handler.response
		self.__baseurl = handler.request.el ["rfc"]
		self.header = r.header
		self.version, self.code, self.msg = r.version, r.code, r.msg		
		self.content_type = None
		self.charset = None
		
		ct = self.get_header ("content-type")
		if ct:
			ctl = ct.split (";")
			self.content_type = ctl [0]
			for param in ctl [1:]:
				if param.strip ().startswith ("charset="):
					self.charset = param.split ("=", 1)[-1].strip ().lower ()
			
		self.connection = self.get_header ("connection")
		self.body = r.get_content ()		
	
	def html (self):
		global has_lxml		
		assert has_lxml is True, "missing lxml or html5lib"
		return treebuilder.Parser, treebuilder.html (self.body, self.__baseurl, self.charset)
	
	def etree (self):
		global has_lxml		
		assert has_lxml is True, "missing lxml or html5lib"
		return treebuilder.Parser, treebuilder.etree (self.body, self.charset)
			
	def binary (self):
		return self.body
		
	def text (self):
		if self.charset:
			return self.body.decode (self.charset)
		else:
			return self.body.decode ("utf8")
		
	def json (self):
		return json.loads (self.text ())
	
	def xmlrpc (self):
		return xmlrpclib.loads (self.text ())	
	
	def save_to (self, path):
		if type (self.body) is None:
			return
			
		if type (self.body) is bytes:
			f = open (path, "wb")
			f.write (self.body)
			f.close ()
			
		else:						
			raise TypeError ("Content is not bytes")
			
			
class RCUInfo:
	def __init__ (self, eurl):
		self.eurl = eurl
	
	def __getattr__ (self, attr):
		try:
			return self.eurl [attr]
		except KeyError:
			raise AttributeError
				
class RCUData:
	def __init__ (self, eurl):
		self.user = eurl.user
	
	def __getattr__ (self, attr):
		try:
			return self.user [attr]
		except KeyError:
			raise AttributeError
				
class ResponseContainer:
	def __init__ (self, handler, callback):
		self.uinfo = RCUInfo (handler.request.el)
		self.udata = RCUData (handler.request.el)
		self.request = RCRequest (handler)
		self.response = RCResponse (handler)
		self.logger = handler.request.logger
		self.__el = handler.request.el
		self.__asyncon = handler.asyncon
		self.callback = callback
		
		for header in handler.response.get_header ():
			if header.lower ().startswith ("set-cookie: "):
				localstorage.localstorage.set_cookie_from_string (
					handler.response.request.el ["rfc"],
					header [12:]
				)
	
	def set_cookie (self, k, v):
		localstorage.localstorage.set_cookie (self.uinfo.rfc, k, v)
	
	def get_cookie (self, k):	
		localstorage.localstorage.get_cookie (self.uinfo.rfc, k)
	
	def set_item (self, k, v):
		localstorage.localstorage.set_item (self.uinfo.rfc, k, v)
	
	def get_item (self, k):	
		localstorage.localstorage.get_item (self.uinfo.rfc, k)
		
	def stall (self, timeout):
		a, b = math.modf (timeout)
		for i in range (int (b)):
			self.__asyncon.set_event_time ()
			time.sleep (1)
		time.sleep (a)
	
	def resolve (self, url):
		return urljoin (self.uinfo.eurl ["rfc"], url)
	
	def inherit (self, surl):
		return self.__el.inherit (surl)
		
	def relocate (self, url):
		from skitai import requests
		requests.add (self.__el.inherit (self.resolve (url), True), self.callback, front = True)
		
	def visit (self, surl, callback = None):
		from skitai import requests
		requests.add (self.inherit (surl), callback and callback or self.callback)
	
	def retry (self):
		from skitai import requests
		self.uinfo.eurl.inc_retrys ()
		requests.add (self.__el, self.callback, front = True)
	
	