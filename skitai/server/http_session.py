import pickle as pickle
from . import http_date
import time
import random
from skitai.lib import pathtool
from skitai.lib import udict
import os, sys
import md5
import urllib.request, urllib.parse, urllib.error
		
class Session:
	def __init__ (self, path, timeout, bsid):
		self.__path = path
		self.__timeout = timeout
		self.__bsid = bsid
		self.__created_time = time.time ()
		self.__last_used = time.time ()
		self.data = data
	
	def __check_timeout (self):
		if time.time () - self.__last_used > self.__timeout:
			self.truncate ()
			raise KeyError("session variable had been timeouted")
			
	def __setitem__ (self, k, v):
		self.data [k] = v
		self.__last_used = time.time ()
		
	def __getitem__ (self, k, v):
		self.__check_timeout ()
		return self.data.get (k, v)
	
	def __delitem__ (self, k, v):
		del self.data [k]
		
	def get_bsid (self):
		return self.__bsid
	
	def get (self, name, default):
		self.__check_timeout ()
		self.__last_used = time.time ()	
		return self.data.get (name, default)
	

class SessionStorage:
	def __init__ (self, path):
		self.path = path
		self.check_directory ()
	
	def check_directory (self):
		if not self.path: return
		for h in list(range(48,58)) + list(range(97,103)):
			for i in list(range(48,58)) + list(range(97,103)):
				for j in list(range(48,58)) + list(range(97,103)):
					initial = "0" + chr (h) + "/" + chr (i) + chr (j)
					pathtool.mkdir (os.path.join (self.path, initial))
	
	def get_filename (self, session):
		if type (session) == type (""):
			bsid = session
		else:	
			bsid = session.get_bsid ()
		return os.path.join (self.path, "0" + bsid[0], bsid[1:3], bsid)
											
	def save (self, session):
		if not self.path: return
		fn = self.get_filename (session)		
		f = open (fn, "wb")
		pickle.dump (session, f)
		f.close ()
		
	def remove (self, session):
		if not self.path: return
		fn = self.get_filename (session)		
		try: os.remove (fn)
		except (OSError): pass	
			
	def load (self, bsid):
		if not self.path: return
		fn = self.get_filename (bsid)		
		f = open (fn, "r")
		session = pickle.load (f)
		f.close ()
		return session
		
	
class Sessions:
	def __init__ (self, path, timeout):
		self.path = path
		self.session_storage = SessionStorage (path)
		self.timeout = timeout
		self.req_count = 0
		self.sessions = {}
		self.load_sessions (self.path)
	
	def make_bsid (self, cookie):
		return md5.new ("%s %s %s" % (
			cookie.request.get_header ("user-agent"), 
			time.time (), 
			random.randrange (1000000)
			)).hexdigest ()
		
	def maintern (self):
		for bsid in list(self.sessions.keys ()):
			session = self.sessions [bsid]
			if time.time () - session.last_used > self.timeout:
				self.remove (bsid)
		
	def get (self, cookie):
		self.req_count += 1
		if self.req_count % 100 == 0:
			self.maintern ()						
		bsid = cookie.get ("BSID")
		if bsid is None:
			bsid = self.make_bsid (cookie)
			cookie.set ("BSID", bsid, "never")
			
		if bsid in self.sessions:			
			session = self.sessions [bsid] 
			if time.time () - session.last_used > self.timeout:
				self.remove (bsid)
		
		if bsid not in self.sessions:
			self.sessions [bsid] = Session (self.path, self.timeout, bsid)
		
		session = self.sessions [bsid]
		return session

	def remove (self, bsid):
		if bsid in self.sessions:
			session = self.sessions [bsid] 
			self.session_storage.remove (session)
			del session
			del self.sessions [bsid]
	
	def load_sessions (self, path):
		for obj in os.listdir (path):
			fn = os.path.join (path, obj)
			if os.path.isdir (fn):
				self.load_sessions (fn)
			else:
				session = self.session_storage.load (fn)	
				self.sessions [session.get_bsid ()] = session
		
	def save_sessions (self):
		for k in self.sessions:
			session = self.sessions [k]
			self.session_storage.save (session)
		
	def cleanup (self):
		self.maintern ()
		self.save_sessions ()
		self.sessions = {}


if __name__ == "__main__":
	def set (name, val = "", expires=None, path = "/", domain = None):
		# browser string cookie
		print(val.serialize ())
		
	
	sess = SecuredCookieValue ({}, "ASDF34x5=DFu$3FD45i&*YTnU+7", set, True)
	sess [3] = (3,4)
	sess.save ()
	
	sess = SecuredCookieValue.unserialize ("zKHqC0mZfX7qyGzVcGGyu3VklHQ=?a=STEKLg==&b=STIKLg==&c=KGxwMQpJMwphSTQKYS4=", "ASDF34x5=DFu$3FD45i&*YTnU+7", set)
	print(sess)
	
	sess = SecuredCookieValue.unserialize ("K05TrqlZvmHtcL461KbiYR+cvjM=?lalala=KEkzCkk0CnRwMQou", "ASDF34x5=DFu$3FD45i&*YTnU+7", set)
	print(sess)
	
	
