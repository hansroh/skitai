import base64
from hashlib import md5
import re
try:
	from urllib.parse import urlparse, quote_plus	
except ImportError:
	from urlparse import urlparse
	from urllib import quote_plus	
import time
from skitai.protocol.http import util
from . import localstorage


class EURL:
	keywords = ('from',)
	methods = ("get", "post", "head", "put", "delete", "options", "trace", "connect", "upload")
	dft_port_map = {'http': 80, 'https': 443, 'ftp': 21}
	DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; Skitaibot/0.1a)"	
	
	def __init__ (self, surl, data = {}):
		self.surl = surl
		self.data = data
		self.user = {}
		self.http = {"http-version": "1.1", "http-connection": "close"}
		self.info = {"depth": 0, "moved": 0, "retrys": 0}
		self.header = {"Cache-Control": "max-age=0"}
		self.parse ()
	
	def __str__ (self):
		return self ["rfc"]
		
	def set_header_from_option (self, k, v):
		"Possibles: http-[auth|form|version|connection|cookie|content-type|user-agent|proxy|tunnel]"
		if k [:5] == "head-":
			self.set_header (k [5:], v)		
		elif k ==	"http-cookie":
			self.set_header ("Cookie", v)
		elif k ==	"http-content-type":
			self.set_header ("Content-Type", v)
		elif k ==	"http-referer":
			self.set_header ("Referer", v)
		self.http [k] = v		
				
	def set_header (self, k, v):
		self.header [k] = v
	
	def del_header (self, key):
		for k, v in list (self.header.items ()):
			if key.lower () == k.lower ():
				del self.header [k]
				
	def get_header (self, key = None, default = None):
		if key:
			for k, v in list (self.header.items ()):
				if key.lower () == k.lower ():
					return v
			return default
		return self.header
						
	def __setitem__ (self, k, v):
		if k [:5] in ("http-", "head-", "wsoc-"):
			self.set_header_from_option (k, v)
		else:	
			self.info [k] = v
	
	def __delitem__ (self, k):
		try:
			del self.info [k]
		except KeyError:
			del self.http [k]	
		
	def __getitem__ (self, k):
		try:
			return self.info [k]
		except KeyError:
			try:
				return self.http [k]
			except KeyError:	
				return None
	
	def get (self, k, d):
		return self.info.get (k) or self.http.get (k, d)
		
	def items (self):
		return list(self.info.items ()) + list(self.http.items ())
	
	def has_key (self, k):
		return k in self.info or k in self.http
			
	def __str__ (self):
		return self ["url"]
	
	def to_version_11 (self):
		self ["http-version"] = "1.1"
		if self ["http-connection"].lower () == "close":
			del self ["http-connection"]
	
	def inc_retrys (self):
		self.info ["retrys"] = self ["retrys"] + 1
	
	def dec_retrys (self):
		self.info ["retrys"] = self ["retrys"] - 1
				
	def inherit (self, surl, moved = False):
		eurl = EURL (surl)
				
		# inherit user-data
		for k, v in list(self.user.items ()):
			if k not in eurl.user: # prevent overwriting
				eurl.user [k] = v
		
		# inherit info
		eurl ["http-auth"] = self ["http-auth"]
		eurl ["referer"] = eurl ["http-referer"] = self ["rfc"]
		eurl ["referer_id"] = self ["page_id"]
		
		if moved:
			eurl ["moved"] = self ["moved"] + 1		
		else:
			eurl ["depth"] = self ["depth"] + 1
			
		# inherit http, header
		for k, v in list(self.http.items ()):
			if k [:5] == "head-":
				eurl [k] = v
			else:
				if k [5:] in ("cookie", "referer", "content-type", "form"):
					continue
				if k not in eurl.http:
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
			
			elif tk [:7] in ("--with-", "--head-", "--http-", "--wsoc-"):				
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
			self.data = {}
						
		self._set (d)

	def	_set (self, d):
		for k, v in list(d.items ()):
			if k [:7] == "--with-":
				k = k [7:]
				self.user [k] = v.strip ()
			elif k in self.methods:
				self ['method'] = k
				self ['url'] = v.strip ()
			elif k == "from":
				self ["referer"] = v.strip ()
				self ["http-referer"] = v.strip ()				
			elif k [:7] in ("--http-", "--head-", "--wsoc-"):
				self [k [2:]] = v.strip ()
			
		self ['scheme'], self ['netloc'], self ['script'], self ['params'], self ['querystring'], self ['fragment'] = urlparse (self ['url'])
		if self ["http-form"] and self ['method'] not in ("post", "put"):
			raise ValueError("Form exists but method isn't post or get")
		if self ["method"] in ("post", "put") and not self ["http-form"]:
			raise ValueError("No form data")
		if not self ["http-form"] and self ["http-content-type"]:
			raise ValueError("Needn't content-type")
		if self ["http-form"] and self ["method"] == "post" and self.get_header ("content-type") is None:
			self ["http-content-type"] = "application/x-www-form-urlencoded; charset=utf-8"		
			
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
			self ["http-auth"], self ['netloc'] = self ['netloc'].split ("@", 1)
		
		if self ["http-auth"]:
			try: 
				self ['username'], self ['password'] = self ["http-auth"].split (':', 1)
			except ValueError:	
				pass
			else:	
				self ["http-auth"] = (self ['username'], self ['password'])
				
		try:
			self ['netloc'], self ['port'] = self ['netloc'].split (':', 1)
		except ValueError:
			self ['netloc'], self ['port'] = self ['netloc'], self.dft_port_map [self ['scheme']]
		
		self ['netloc'] = self ['netloc'].lower ()
		try: self ['port'] = int (self ['port'])
		except: self ['port'] = 80
		
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
		
		self ["page_id"] = self.geneate_page_id ()
		
		ua = self ["http-user-agent"]
		if ua is None:			
			self ["http-user-agent"] = self.DEFAULT_USER_AGENT
		
		# set cookie
		ls = localstorage.localstorage
		cookie = self ["http-cookie"]
		if cookie:
			ls.set_cookie_from_data (self ["rfc"], cookie)					
		cookie = ls.get_cookie_as_string (self ["rfc"])		
		if cookie:
			self ["http-cookie"] = cookie
		
	def get_connection (self):
		return self ["http-connection"]
				
	def get_useragent (self):
		return self ["http-user-agent"]
	
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

	def geneate_page_id (self):		
		signature = self ['method'] + "|" + self ['netloc'] + "|" + str (self ["port"]) + "|" + self ['script'] + "|" + self ['params']
		if self ['querystring']:
			signature += "|" + self.__sort_args (self ['querystring'])
		if self ['http-form']:
			signature += "|" + self.__sort_args (self ['http-form'])
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
