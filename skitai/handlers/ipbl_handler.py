import os, time

class Handler:	
	maintern_interval = 180
	
	def __init__ (self, wasc, blacklist_dir):
		self.wasc = wasc		
		self.blacklist_dir = blacklist_dir		
		self.blacklist = {}
		self.last_maintern = 0.
	
	def maintern (self):
		try:
			ips = os.listdir (self.blacklist_dir)
		except OSError:
			return
		
		self.blacklist = {}
		for ip in ips:
			self.blacklist [ip] = None
	
	def detect (self, request):
		if not self.blacklist:
			return 0
			
		cl = request.addr [0]
		if cl in self.blacklist:
			return 1
			
		s = cl.rfind (".")
		if cl [:s - 1] in self.blacklist:
			return 1
			
		return 0
		
	def match (self, request):
		ctime = time.time ()
		if ctime - self.last_maintern > self.maintern_interval:
			self.maintern ()
			self.last_maintern = ctime
		return self.detect (request)
		
	def handle_request (self, request):
		request.abort (403, "Access Denied")
	