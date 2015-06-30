import asynchat, asyncore, DNS, socket, re, rfc822, sys, time

OLDSTYLE_AUTH = re.compile(r"auth=(.*)", re.I)
CRLF = "\r\n"

class DNSNotFound (Exception): pass

def quoteaddr(addr):
	m = (None, None)
	try:
		m=rfc822.parseaddr(addr)[1]
	except AttributeError:
		pass
	if m == (None, None):
		return "<%s>" % addr
	else:
		return "<%s>" % m

def quotedata(data):
	return re.sub (r'(?m)^\.', '..',
		re.sub(r'(?:\r\n|\n|\r(?!\n))', CRLF, data))
				

class SMTP (asynchat.async_chat):
	DNSHOST='164.124.101.2'
	def __init__(self, composer, logger = None):
		self.composer = composer						
		self.logger = logger
		
		self.__ltime = time.time ()
		self.__line = []
		self.__mline = []
		self.__code = 900
		self.__resp = ""
		self.__stat = 0		
		self.__sent = 0
		self.__panic = 0
		self.does_esmtp = 1
		self.esmtp_features = {}
		
		asynchat.async_chat.__init__(self)
		
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		self.set_terminator (CRLF)
		
		self.sendmail ()
	
	def get_time (self):
		return self.__ltime
		
	def push (self, msg):
		asynchat.async_chat.push(self, msg + '\r\n')
	
	def compact_traceback(self):	
		return str (sys.exc_info() [0])
	
	def mxlookup(self, host, qtype = "mx"):
		a = DNS.DnsRequest(host, qtype = qtype, server=self.DNSHOST, timeout = 3).req().answers
		l = map(lambda x:x['data'], a)
		l.sort()
		return l
	
	def sendmail (self):
		try:
			hostlist = self.get_mx ()
					
			if not hostlist:
				self.__code, self.__resp = 901, "DNS Not Found"
				raise DNSNotFound
			
			hostcount = len (hostlist)
			
			for i in range (len (hostlist)):
				prior, host = hostlist [i]
				try:
					self.connect ((host, 25))
					self.address = host
					return
					
				except:
					if i == hostcount - 1:
						self.__code, self.__resp = 900, "SMTP Connection Failed"			
						raise
					else:
						continue
		except:
			self.handle_error ()
	
	def get_mx(self):
		_toHost = self.composer.get_HOST ()
		
		resolved = self.mxlookup(_toHost)
		if not resolved:
			resolved = map (lambda x: (0, x), self.mxlookup(_toHost, 'a'))
			
		return resolved

	def collect_incoming_data (self, data):
		self.__line.append(data)
	
	def get_reply (self, line):
		code = line [:3]		
		try:
			code = int (code)
			resp = line [4:]
		except:	
			code = -1
			resp = ""
		
		return code, resp
	
	def has_extn(self, opt):
		return self.esmtp_features.has_key(opt.lower())
			
	def found_terminator(self):
		line = "".join(self.__line)
		self.__line = []				
		
		code, _resp = self.get_reply (line)
		
		if code == -1:
			self.__code, self.__resp = 801, "SMTP Server Response Error"
			self.close ()
			return
			
		self.__mline.append (_resp)
		
		if line [3:4] == "-":
			return
			
		else:
			for each in self.__mline [1:]:
				auth_match = OLDSTYLE_AUTH.match(each)
				if auth_match:
					self.esmtp_features["auth"] = self.esmtp_features.get("auth", "") \
							+ " " + auth_match.groups(0)[0]
					continue
	
				m=re.match(r'(?P<feature>[A-Za-z0-9][A-Za-z0-9\-]*)',each)
				if m:
					feature=m.group("feature").lower()
					params=m.string[m.end("feature"):].strip()
					if feature == "auth":
						self.esmtp_features[feature] = self.esmtp_features.get(feature, "") \
								+ " " + params
					else:
						self.esmtp_features[feature]=params
			
			resp = " ".join (self.__mline)
			self.__mline = []
		
		if self.__stat == 0:
			if code != 220:
				self.__code, self.__resp = code, resp
				self.__stat = 9
				self.push ("quit")
				return
			self.__stat = 1
			self.push ("ehlo %s" % socket.getfqdn())
		
		elif self.__stat == 1:
			if not (200 <= code <= 299):
				self.__code, self.__resp = code, resp
				self.__stat = 2
				self.push ("helo %s" % socket.getfqdn())
				return
				
			self.__stat = 3
			if self.does_esmtp and self.has_extn('size'):
				option = "size=" + `len(self.composer.get_DATA ())`				
				self.push ("mail FROM:%s %s" % (quoteaddr (self.composer.get_FROM ()), option))
			else:
				self.push ("mail FROM:%s" % (quoteaddr (self.composer.get_FROM ())))

		elif self.__stat == 2:	
			if not (200 <= code <= 299):
				self.__code, self.__resp = code, resp
				self.__stat = 9
				return
			self.__stat = 3
			self.push ("mail FROM:%s" % quoteaddr (self.composer.get_FROM ()))
			
		elif self.__stat == 3:
			if not (200 <= code <= 299):
				self.__code, self.__resp = code, resp
				self.__stat = 8
				self.push ("rset")
				return				
			self.__stat = 4
			self.push ("rcpt TO:%s" % quoteaddr (self.composer.get_TO ()))
			
		elif self.__stat == 4:
			if not (250 <= code <= 251):				
				self.__code, self.__resp = code, resp
				self.__stat = 8
				self.push ("rset")
				return
			self.__stat = 5
			self.push ("data")
		
		elif self.__stat == 5:
			if code != 354:
				self.__code, self.__resp = code, resp
				self.__stat = 8
				self.push ("rset")
				return
			self.__stat = 8
			
			q = quotedata(self.composer.get_DATA ())
			if q[-2:] != CRLF:
				q = q + CRLF
			q = q + "."
			self.__sent = 1
			self.push (q)
				
		elif self.__stat == 8:
			if self.__sent and code == 250:
				self.__code, self.__resp = -250, "OK"
			elif self.__sent:
				self.__code, self.__resp = code, resp								
			self.__stat = 9
			self.push ("quit")
			
		else:
			self.handle_close ()	
		
	def handle_connect (self):
		self.__ltime = time.time ()
	
	def close (self):
		self.composer.set_response (self.__code, self.__resp)
		asynchat.async_chat.close (self)
		
	def handle_error (self):
		self.__resp = self.compact_traceback ()		
		if self.logger:
			self.logger.trace ()
		else:
			print asnycore.compact_traceback ()
		self.close()
		
	def handle_close (self):
		self.close()
			
	def handle_expt (self):
		self.__panic += 1
		if self.__panic > 3:		
			self.__code = 802
			self.__resp = "Socket panic"
			self.close ()
	
	def handle_read (self):
		self.__ltime = time.time ()
		return asynchat.async_chat.handle_read (self)

	def handle_write(self):
		self.__ltime = time.time ()
		return asynchat.async_chat.handle_write (self)
    
	def handle_timeout (self):
		self.__code, self.__resp = 800, "Timeout"
		self.close ()
			
			
if __name__ == "__main__":		
	for i in range (2):
		SMTP ("hansroh@gmail.com", "hansroh@_lufexx.com", "jh ghjgjh gjh gjhgjh  kkjhkjhkjhk")
		
	asyncore.loop ()

