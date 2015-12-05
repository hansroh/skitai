import base64
from hashlib import md5
import re
try:
	from urllib.parse import urlparse, quote_plus	
except ImportError:
	from urlparse import urlparse
	from urllib import quote_plus	
import time
from . import util
from . import localstorage


class EURL:
	keywords = ('from',)
	methods = ("get", "post", "head", "put", "delete", "options", "trace", "connect")
	dft_port_map = {'http': 80, 'https': 443, 'ftp': 21}
	DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; Skitaibot/0.1a"	
	
	def __init__ (self, surl, data = {}):
		self.surl = surl
		self.data = data
		self.info = {"surf": 0, "http-version": "1.1"}
		self.header = {}
		self.parse ()
	
	def set_header (self, k, v):
		self.header [k] = v
			
	def get_header (self, key = None):
		if key:
			for k, v in list (self.header.items ()):
				if key.lower () == k.lower ():
					return v
			return None
		return self.header
						
	def __setitem__ (self, k, v):
		self.info [k] = v
	
	def __delitem__ (self, k):
		del self.info [k]
		
	def __getitem__ (self, k):
		try:
			return self.info [k]
		except KeyError:
			return None	
	
	def get (self, k, d):
		return self.info.get (k, d)
		
	def items (self):
		return list(self.info.items ())
	
	def has_key (self, k):
		return k in self.info
			
	def __str__ (self):
		return self ["url"]
	
	def advance (self, surl, **karg):
		eurl = EURL (surl)
		for k, v in list(self.items ()):
			if k in ("querystring", "http-form", "framgment", "params", "referer", "rid"):
				continue
			elif k == "pageid":
				self ["refererid"] = v
				continue
			if k in eurl: # not overwrite
				continue
			eurl [k] = v
		eurl ["referer"] = self ["url"]
		eurl ["surf"] = self ["surf"] + 1
		
		for k, v in list(karg.items ()):
			eurl [k] = v
		
		return eurl
		
	def parse (self):
		d = {}
		current_key = None
		for token in self.surl.split(" "):
			tk = token.lower()
			if tk in self.keywords or tk in self.methods:
				current_key = tk
				d[current_key] = ''
			
			elif tk [:7] in ("--with-", "--head-", "--http-"):
				current_key = token
				d[current_key] = ''
				
			else:
				try: 
					if d[current_key]:
						 d[current_key] += ' ' + token
					else:
							d[current_key] = token
							
				except KeyError:
					current_key = 'get'					
					d[current_key] = token
		
		if self.data:
			d ["http-form"] =  util.dictencode (self.data)
						
		self._set (d)

	def	_set (self, d):
		for k, v in list(d.items ()):
			if k == "from":
				k = "referer"
			elif k in self.methods:
				self ['method'] = k
				self ['url'] = v
				continue
			elif k [:7] == "--http-":
				self [k [2:]] = v
				continue
			elif k [:7] == "--head-":
				self.set_header (k [7:], v)
				continue
			elif k [:7] == "--with-":
				k = k [7:]
			self [k] = v
			
		self ['scheme'], self ['netloc'], self ['script'], _params, _query, _fragment = urlparse (self ['url'])
		if _params: self ['params'] = _params
		if _query: self ['querystring'] = _query
		if _fragment: self ['fragment'] = _fragment
		
		if self ["http-form"] and self ['method'] not in ("post", "put"):
			raise ValueError("Recieved form but method is not post or get")
		
		if self ["method"] in ("post", "put") and not self ["http-form"]:
			raise ValueError("No form data")
				
		if self ['scheme'] not in ("http", "https"):
			self ['scheme'] = "http"
		if not self ['script']: 
			self ['script'] = '/'
		if self ['querystring']:
			try: self ['querystring'] = uitl.strencode (self ['querystring'])
			except: pass
		
		uri = self ['script'] #real request uri
		if self ['params']:
			uri += ';' + self ['params']
		if self ['querystring']:
			uri += '?' + self ['querystring']
		self ['uri'] = uri

		position = self ['netloc'].find('@')
		if position > -1:
			auth, netloc = self ['netloc'].split ("@", 1)
			self ['netloc'] = netloc
			try: 
				self ['username'], self ['password'] = auth.split (':', 1)
			except ValueError:	
				pass
			else:	
				self ['auth'] = base64.encodestring ('%s:%s' % (self ['username'], self ['password']))[:-1]
				
		try:
			self ['netloc'], self ['port'] = self ['netloc'].split (':', 1)
		except ValueError:
			self ['netloc'], self ['port'] = self ['netloc'], self.dft_port_map [self ['scheme']]
		
		self ['netloc'] = self ['netloc'].lower ()
		try: self ['port'] = int (self ['port'])
		except: self ['port'] = 80
		
		self ['headerhost'] = self ['netloc']
		if self ['scheme'] == "https" and self ['port'] != 443:
			self ['headerhost'] += ":" + self ['port']
		elif self ['scheme'] == "http" and self ['port'] != 80:
			self ['headerhost'] += ":" + str (self ['port'])
		
		netloc = self ['netloc']
		netloc2 = netloc.split (".")
		if len (netloc2 [-1]) == 3:
			self ['domain'] = ".".join (netloc2 [-2:])
			self ['host'] = ".".join (netloc2 [:-2])
			if not self ['host']:
				self ['host'] = "www"
		elif len (netloc2 [-1]) == 2:
			if len (netloc2) == 2:
				self ['domain'] = ".".join (netloc2)
				self ['host'] = "www"
			elif len (netloc2) == 3:
				if netloc2 [0] == "www":
					self ['domain'] = ".".join (netloc2 [-2:])
				else:
					self ['domain'] = ".".join (netloc2)
				self ['host'] = "www"
			else:
				self ['domain'] = ".".join (netloc2 [-3:])
				self ['host'] = ".".join (netloc2 [:-3])
			
		try: dft_port = self.dft_port_map [self ['scheme']]
		except KeyError:
			self ['rfc'] = '%s://%s:%d%s' % (self ['scheme'], self ['netloc'], self ['port'], self ['uri'])
		else:
			if dft_port == self ['port']:
				self ['rfc'] = '%s://%s%s' % (self ['scheme'], self ['netloc'], self ['uri'])
			else:
				self ['rfc'] = '%s://%s:%d%s' % (self ['scheme'], self ['netloc'], self ['port'], self ['uri'])
		
		self ["pageid"] = self.get_pageid ()
		
		connection = self.get_header ("connection")
		if self ["http-version"] == "1.1":
			if connection is None:
				self ["connection"] = "keep-alive"
			else:
				self ["connection"] = connection
		else:
			if connection is None:
				self ["connection"] = "close"
			else:
				self ["connection"] = connection			
			
	def get_useragent (self):
		ua = self.get_header ("user-agent")
		return ua is not None and ua or self.DEFAULT_USER_AGENT
			
	def make_request_header (self):
		request = []
		if self ["http-proxy"]:
			request.append ("%s %s HTTP/%s" % (self ["method"].upper (), self ["rfc"], self ["http-version"]))			
		else:	
			request.append ("%s %s HTTP/%s" % (self ["method"].upper (), self ["uri"], self ["http-version"]))
		
		if self.get_header ("host") is None:
			request.append ("Host: %s" % self ["headerhost"])
		
		request.append ("Accept-Encoding: gzip, deflate")
		#request.append ("Accept-Encoding: identity")
		request.append ("Cache-Control: max-age=0")
		request.append ("Accept: */*")
		
		# set cookie
		if self.get_header ("cookie") is None:
			ls = localstorage.localstorage
			cookie = self ["cookie"]
			if cookie and ls:
				ls.set_default_cookie (self ["rfc"], cookie)		
			if ls:
				cookie = ls.get_cookie_string (self ["rfc"])			
			if cookie:
				request.append ("Cookie: %s" % cookie)
			
		# set referer
		if self.get_header ("referer") is None:
			referer = self ["referer"]
			if referer:	
				request.append ("Referer: %s" % referer)
		
		# set user agent
		if self.get_header ("user-agent") is None:
			request.append ("User-Agent: %s" % self.DEFAULT_USER_AGENT)	
		
		# set authorization info.
		if self ["auth"]:
			request.append ("Authorization: Basic %s" % self ["auth"])
		
		# post method header	
		if self ["http-form"]:			
			if self.get_header ("content-type") is None:
				request.append ("Content-Type: application/x-www-form-urlencoded; charset=utf8")
			request.append ("Content-Length: %d" % len (self ["http-form"]))
		
		# additional request header
		for k, v in list (self.get_header ().items ()):
			request.append ("%s: %s" % (k.strip (), v.strip ()))
		
		request = '\r\n'.join (request) + '\r\n\r\n'
		# form data		
		if self ["method"] == 'post':
			request += self ["http-form"]
		return request
		
	def __sort_args (self, data):
		args = {}
		for arg in data.split ("&"):
			try: k, v = arg.split ("=")
			except: continue
			if v:
				args [k] = v
						
		args = list(args.items ())
		args.sort ()
		
		argslist = []
		for k, v in args:
			argslist.append ("%s=%s" % (k, v))
		
		argslist.sort ()		
		return "&".join (argslist)

	def get_pageid (self):		
		signature = self ['netloc'] + "|" + str (self ["port"]) + "|" + self ['script']
		if self ['querystring']:
			signature += "|" + self.__sort_args (self ['querystring'])
		if self ['data']:
			signature += "|" + self.__sort_args (self ['data'])
		return md5 (signature.encode ("utf8")).hexdigest ()
	
	def show (self):
		for k, v in list(self.info.items()):
			print("-%s: %s" % (k.upper(), v))




def test_crack_uql():
	d = (
		  "get http://hans:whddlgkr@target_site.com:8089/rpc2/agent.status?a=x#eter "
		  "with-ua ELAB robotec. with-sid 34543"
		  )
	EURL (d).show()
	print("------------")
	d = "post http://www.dsfds.com/asdsa.aps?asdas=1&sdfds=1 with-form a=a&b=432432"
	EURL (d).show()
	

if __name__ == "__main__":
	test_crack_uql ()
