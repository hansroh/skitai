import urlparse
import base64
import md5
import re
import time
import xmlrpclib
import util

class EURL:
	keywords = ('get', 'post', 'head', 'put', 'from')
	dft_port_map = {'http': 80, 'https': 443, 'ftp': 21}
	def __init__ (self, surl):
		self.surl = surl
		self.info = {"surf": 0, "ver": "1.1"}
		self.parse ()
		
	def __setitem__ (self, k, v):
		self.info [k] = v
	
	def __delitem__ (self, k):
		del self.info [k]
		
	def __getitem__ (self, k):
		if k == "pid" and not self.has_key ("pid"):
			self ["pid"] = self.hexdigest ()
			return self ["pid"]
			
		try:
			return self.info [k]
		except KeyError:
			return None	
	
	def get (self, k, d):
		return self.info.get (k, d)
		
	def items (self):
		return self.info.items ()
	
	def has_key (self, k):
		return self.info.has_key (k)
			
	def __str__ (self):
		return self ["url"]
	
	def advance (self, surl, **karg):
		eurl = EURL (surl)
		for k, v in self.items ():
			if k in ("querystring", "form", "framgment", "params", "referer", "pid"):
				continue
			if eurl.has_key (k): # not overwrite
				continue
			eurl [k] = v
		eurl ["referer"] = self ["url"]
		eurl ["surf"] = self ["surf"] + 1
		
		for k, v in karg.items ():
			eurl [k] = v
			
		return eurl
		
	def parse (self):
		d = {}
		current_key = None
		for token in self.surl.split(" "):
			tk = token.lower()
			if tk in self.keywords:
				current_key = tk
				d[current_key] = ''
			elif tk.startswith ("with-"):
				current_key = tk [5:]
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
		self._set (d)

	def	_set (self, d):
		for k, v in d.items ():
			if k == "from":
				k = "referer"
			elif k in ("get", "post", "head", "put"):
				self ['method'] = k
				self ['url'] = v
				continue
			self [k] = v
		
		self ['scheme'], self ['netloc'], self ['script'], _params, _query, _fragment = urlparse.urlparse (self ['url'])
		if _params: self ['params'] = _params
		if _query: self ['querystring'] = _query
		if _fragment: self ['fragment'] = _fragment
		
		if self ["method"] == "post" and self ["form"] is None:
			self ["form"] = self ['querystring']
			self ['querystring'] = ""
					
		if self ['scheme'] not in ("http", "https"):
			self ['scheme'] = "http"
		if not self ['script']: 
			self ['script'] = '/'
		if self ['querystring']:
			try: self ['querystring'] = uitl.queryencode (self ['querystring'])
			except: pass
		if self["mehotd"] == "post":
			if not self ['form']:
				raise ValueError, "post method but no form data"		
			try: self ['form'] = uitl.queryencode (self ['form'])
			except: pass
		
		if self ['cookie']:
			self ['cookie'] = util.strparse (self ['cookie'], 1)
		if self ['header']:	
			self ['header'] = util.strparse (self ['header'], 0)

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
			self ['headerhost'] += ":" + self ['port']
		
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
	
	def make_request_header (self, localstorage = None):
		request = []
		if self ["proxy"]:
			request.append ("%s %s HTTP/%s" % (self ["method"].upper (), self ["rfc"], self ["ver"]))			
		else:	
			request.append ("%s %s HTTP/%s" % (self ["method"].upper (), self ["uri"], self ["ver"]))
		request.append ("Host: %s" % self ["headerhost"])
		if self ["keep-alive"]:
			request.append ("Keep-Alive: %s" % self ["keep-alive"])
			request.append ("Connection: keep-alive")
		else:
			request.append ("Connection: close")	
		#request.append ("Accept-Encoding: gzip, deflate")
		request.append ("Accept-Encoding: identity")
		request.append ("Cache-Control: max-age=0")
		request.append ("Accept: */*")
		
		# set cookie
		cookie = self ["cookie"]
		if cookie and localstorage:
			localstorage.set_default_cookie (self ["rfc"], cookie)		
		if localstorage:
			cookie = localstorage.get_cookie_string (self ["rfc"])			
		if cookie:	
			request.append ("Cookie: %s" % cookie)
			
		# set referer
		referer = self ["referer"]
		if referer:	
			request.append ("Referer: %s" % referer)
		
		# set user agent
		if self ["ua"]:
			request.append ("User-Agent: %s" % ua)
		else:
			request.append ("User-Agent: Mozilla/5.0 (Windows NT 6.1; rv:39.0) Gecko/20100101 Firefox/39.0")	
		
		# set authorization info.
		if self ["auth"]:
			request.append ("Authorization: Basic %s" % auth)
		
		# post method header	
		if self ["form"]:
			request.append ("Content-Type: application/x-www-form-urlencoded")
			request.append ("Content-Length: %d" % len (self ["form"]))
		
		# additional request header
		if self ["header"]:
			for each in self ["header"].split (";"):
				for k, v in each.split (":", 1):
					request.append ("%s: %s" % (k.strip (), v.strip ()))
		
		request = '\r\n'.join (request) + '\r\n\r\n'
		# form data		
		if self ["method"] == 'post':
			request += self ["form"]
		return request
		
	def __sort_args (self, data):
		args = {}
		for arg in data.split ("&"):
			try: k, v = arg.split ("=")
			except: continue
			if v:
				args [k] = v
						
		args = args.items ()
		args.sort ()
		
		argslist = []
		for k, v in args:
			argslist.append ("%s=%s" % (k, v))
		
		argslist.sort ()		
		return "&".join (argslist)

	def hexdigest (self):
		signature = self ['netloc'] + "|" + str (self ["port"]) + "|" + self ['script']
		if self ['querystring']:
			signature += "|" + self.__sort_args (self ['querystring'])
		if self ['data']:
			signature += "|" + self.__sort_args (self ['data'])
		return md5.new (signature).hexdigest ()
	
	def show (self):
		for k, v in self.info.items():
			print "-%s: %s" % (k.upper(), v)


def test_crack_uql():
	d = (
		  "get http://hans:whddlgkr@target_site.com:8089/rpc2/agent.status?a=x#eter "
		  "with-ua ELAB robotec. with-sid 34543"
		  )
	EURL (d).show()
	print "------------"
	d = "post http://www.dsfds.com/asdsa.aps?asdas=1&sdfds=1 with-form a=a&b=432432"
	EURL (d).show()
	

if __name__ == "__main__":
	test_crack_uql ()
