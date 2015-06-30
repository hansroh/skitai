from skitai.protocol.dns import asyndns
import time

class DNSCache:
	def __init__ (self, logger = None):		
		self.dns = asyndns.Request (logger)
		self.logger = logger
		self.cache = {}
		self.hits = 0

	def set (self, answers):
		if answers:		
			name = answers [0] ["name"]
			answer = answers [-1]			
			for each in answers:
				name = each ["name"]
				if not self.cache.has_key (name):
					self.cache [name] = {}			
				if answer.has_key ("ttl"):
					answer ["valid"]	= time.time () + answer ["ttl"]
				self.cache [name][answer ["typename"]] = [answer]
			
	def expire (self, host):
		try: del self.cache [host]
		except KeyError: pass		

	def get (self, host, qtype = "A", check_ttl = False):
		try: answers = self.cache [host][qtype]
		except KeyError: return []
		answer = answers [0]
		if not answer.has_key ("valid"):
			return [answer]
		else:
			if check_ttl and answer ["valid"] < time.time ():
				del self.cache [host][qtype]
				return []
			else:
				return [answer]
	
	def is_ip (self, name):
		arr = name.split (".")
		if len (arr) != 4: return False
		try: arr = filter (lambda x: x & 255 == x, map (int, arr))
		except ValueError: 
			return False
		if len (arr) != 4: return False
		return True
		
	def __call__ (self, host, qtype, callback):
		self.hits += 1
		hit = self.get (host, qtype, True)
		if hit: 
			return callback (hit)
	
		if self.is_ip (host):
			self.set ([{"name": host, "data": host, "typename": qtype}])
			return callback ([{"name": host, "data": host, "typename": qtype}])
		
		try:
			self.dns.req (host, qtype = qtype, protocol = "tcp", callback = [self.set, callback])
		except:
			self.logger.trace (host)
			callback ([])


query = None

def init (logger):
	global query
	if query is None:
		query = DNSCache (logger)	

def get (name, qtype = "A"):	
	global query
	return query.get (name, qtype, False)
	
