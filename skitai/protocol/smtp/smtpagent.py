import threading, time, Queue, asyncore, os, sys
import async_smtp
import dummy_smtpserver, composer
import types

class ExQueue (Queue.Queue):
	def get(self, block=True, timeout=None, exclude = {}):
		self.not_empty.acquire()
		try:
			if not block:
				if self._empty():
					raise Queue.Empty
			elif timeout is None:
				while self._empty():
					self.not_empty.wait()
			else:
				if timeout < 0:
					raise ValueError("'timeout' must be a positive number")
				endtime = _time() + timeout
				while self._empty():
					remaining = endtime - _time()
					if remaining <= 0.0:
						raise Queue.Empty
					self.not_empty.wait(remaining)
			item = self._get(exclude)			
			self.not_full.notify()
			return item
			
		finally:
			self.not_empty.release()			
			
	def _get(self, exclude):
		for i in range (len (self.queue)):
			item = self.queue.popleft ()
			host = item.get_HOST ()
			concurrents = exclude.get (host, 0)
			if concurrents < 2:
				return item
			else:
				self.queue.append (item)
			

class SMTPAgent:
	def __init__ (self, socket_pool_count, logger = None, test_email = None):
		self.q = ExQueue (int (socket_pool_count * 2))
		self.socket_pool_count = socket_pool_count
		self.logger = logger
		self.result = []
		self.test_email = test_email
		self.composers = {}
		threading.Thread (target = self.sendloop).start ()
	
	def create_composer (self, item):
		try:
			msg = composer.Composer (
				rcpt = self.test_email,
				fn = item
				)
			# challange email address
			msg.get_HOST ()
			return msg
			
		except:
			try: os.remove (item)
			except OSError: pass
			self.logger.trace ()
			
			try:
				msg
			except: 
				self.set_result (("-1", 961, str (sys.exc_info() [0]), ""))
			else: 
				self.set_result ((msg.get_UID (), 960, "Email address error", msg.get_reciever ()))
	
	def get_result (self):
		result, self.result = self.result, []		
		return result
		
	def set_result (self, r):
		self.result.append (r)
		
	def put (self, item):
		if type (item) is types.StringType:
			msg = self.create_composer (item)
			if msg: self.q.put (msg)
		else:
			self.q.put (item)
	
	def maintern (self):	
		for obj in asyncore.socket_map.values ():
			if isinstance (obj, async_smtp.SMTPClient):
				_ltime = obj.get_time ()
				if time.time () - _ltime > 60:
					obj.handle_timeout ()
				
		dup = {}
		for obj in self.composers.keys ():
			r = obj.get_response ()
			if not r:
				host = obj.get_HOST ()
				try: 
					dup [host] += 1
				except KeyError:
					dup [host] = 1
					
			else:
				self.set_result (r)
				obj.removeFile ()
				del self.composers [obj]
						
		return dup
		
	def ex_get (self, dup):
		return self.q.get (exclude = dup)
	
	def asyncloop (self):
		try:
			asyncore.loop (timeout = 3, count = 1)
		except:
			self.logger.trace ()	
				
	def sendloop (self):		
		while 1:
			dup = {}
			if self.composers:
				dup = self.maintern ()
			
			if not self.q.qsize () and not asyncore.socket_map:
				time.sleep (3)
				continue
			
			self.asyncloop ()
			
			if len (asyncore.socket_map) > self.socket_pool_count: continue
			if not self.q.qsize (): continue			
			item = self.ex_get (dup)
			if not item: continue
			
			self.composers [item] = None
			async_smtp.SMTPClient (item, self.logger)
			
	
	def status (self):
		return {
			"Asyncore sockets": len (asyncore.socket_map),
			"Email queue": self.q.qsize (),
			"Current jobs": len (self.composers)
		}


def create (pools, logger, test_email, smtpd = 0):
	if smtpd:
		dummy_smtpserver.SMTPServer (("localhost", 25), None)	
	return SMTPAgent (pools, logger, test_email)
	
