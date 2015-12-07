"""
2015. 12. 7 Hans Roh

LocalStorage
	cookie
	item
	
ResponseContainer
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
		encoding
		body
"""

import json
try:
	import xmlrpclib
except ImportError:
	import xmlrpc.client as xmlrpclib
from . import localstorage
	
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
		
	def get_header (self, header):
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
			return None
		else:
			return hc[header]

class RCResponse (RCRequest):
	def set (self, handler):	
		r = handler.response
		self.header = r.header
		self.version, self.code, self.msg = r.version, r.code, r.msg
		
		self.content_type = None
		self.encoding = None
		
		ct = self.get_header ("content-type")
		if ct:
			ctl = ct.split (";")
			self.content_type = ctl [0]
			for param in ctl [1:]:
				if param.strip ().startswith ("charset="):
					self.encoding = param.split ("=", 1)[-1].strip ().lower ()
			
		self.connection = self.get_header ("connection")
		self.body = r.get_content ()		
	
	def binary (self):
		return self.body
		
	def text (self):
		if self.encoding:
			return self.body.decode (self.encoding)
		else:
			return self.body.decode ("utf8")
		
	def json (self):
		return json.loads (self.body)
	
	def xmlrpc (self):
		return xmlrpclib.loads (self.body)	
	
	def save_to (self, path):
		content = self.get_content ()
		if type (content) is bytes:
			f = open (path, "wb")
			f.write (content)
			f.close ()
		else:
			raise TypeError ("Content is not bytes")
			
			
class RCUInfo:
	def __init__ (self, eurl):
		self.eurl = eurl
		del self.eurl.data
	
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
	def __init__ (self, handler):
		self.uinfo = RCUInfo (handler.request.el)
		self.udata = RCUData (handler.request.el)
		self.request = RCRequest (handler)
		self.response = RCResponse (handler)
		
		for header in handler.response.get_headers ():
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
	
	def url_for (self, surl):
		return self.uinfo.eurl.inherit (surl)

