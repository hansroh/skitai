#!/usr/bin/python3
# 2015. 11. 27 by Hans Roh hansroh@gmail.com

import sys, os, getopt
from skitai import lifetime
from aquests.lib import flock, pathtool, logger
from aquests.lib.athreads import select_trigger
from aquests.protocols.smtp import async_smtp, composer
import signal
import time
import glob
from skitai.server.wastuff import daemon

def hTERM (signum, frame):			
	lifetime.shutdown (0, 30.0)

def hKILL (signum, frame):			
	lifetime.shutdown (0, 1.0)

def hHUP (signum, frame):			
	lifetime.shutdown (3, 30.0)


class	SMTPDeliverAgent (daemon.Daemon):
	CONCURRENTS = 4
	MAX_RETRY = 10
	UNDELIVERS_KEEP_MAX = 2592000
	NAME = "smtpda"

	def __init__ (self, config, logpath, varpath, consol):
		self.que = {}
		self.actives = {}
		daemon.Daemon.__init__ (self, config, logpath, varpath, consol)
	
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 1:
			self.shutdown_in_progress = True
	
	def close (self):
		self.logger ("[info] service %s stopped" % self.NAME)
						
	def run (self):
		self.logger ("[info] service %s started" % self.NAME)
		try:
			try:
				lifetime.loop (os.name == 'nt' and 2.0 or 30.0)
			except KeyboardInterrupt:
				pass	
			except:
				self.logger.trace ()
		finally:
			self.close ()		
	
	def maintern_shutdown_request (self, now):
		req = daemon.Daemon.maintern_shutdown_request (self, now)
		if daemon.EXIT_CODE is not None:
			if req == "terminate":
				lifetime.shutdown (0, 30.0)
			elif req == "kill":
				lifetime.shutdown (0, 1.0)	
			elif req == "restart":
				lifetime.shutdown (3, 30.0)
						
	def setup (self):
		self.make_logger ()
		self.bind_signal (hTERM, hKILL, hHUP)		
		
		val = self.config.get ("max_retry", 10)
		if val: self.MAX_RETRY = val
		val = self.config.get ("keep_days", 30)
		if val: self.UNDELIVERS_KEEP_MAX = val * 3600 * 24

		self.default_smtp = (
			self.config.get ("smtpserver"),
			self.config.get ("user"),
			self.config.get ("password"),
			self.config.get ("ssl") and True or False
		)
		
		# dummy file like object for keeping lifetime loop
		if os.name == "nt":
			select_trigger.trigger.address = ('127.9.9.9', 19998)
		select_trigger.trigger ()
		
		self.path_spool = os.path.join (self.varpath, "mail", "spool")
		pathtool.mkdir (self.path_spool)
		composer.Composer.SAVE_PATH = self.path_spool
		
		self.path_undeliver = os.path.join (self.varpath, "mail", "undeliver")
		pathtool.mkdir (self.path_undeliver)
		
		lifetime.init ()		
		lifetime.maintern.sched (3.0, self.handle_spool)		
		if os.name == "nt":			
			lifetime.maintern.sched (10.0, self.maintern_shutdown_request)		
		
	def send (self):
		if self.shutdown_in_progress:
			return
			
		while self.que:
			fn = self.que.popitem () [0]
			if fn in self.actives: continue

			self.actives [fn] = time.time ()
			path = os.path.join (self.path_spool, fn)
			cmps = composer.load (path)
			if cmps.get_SMTP () is None:
				cmps.set_smtp (*self.default_smtp)
			if cmps.is_SSL ():
				request = async_smtp.SMTP_SSL
			else:	
				request = async_smtp.SMTP
			request (cmps, self.logger, self.when_done)					
			break
	
	def when_done (self, cmps, code, reps):
		fn = os.path.split (cmps.get_FILENAME ()) [-1]
		
		if code == -250:
			cmps.remove ()
		else:
			if cmps.get_RETRYS () > self.MAX_RETRY:
				cmps.moveto (self.path_undeliver)
			else:	
				cmps.moveto (self.path_spool)		
		del self.actives [fn]
		self.send ()
	
	def maintern (self, current_time):
		for path in glob.glob (os.path.join (self.path_undeliver, "*.*")):
			mtime = os.path.getmtime (path)
			if mtime + self.UNDELIVERS_KEEP_MAX > current_time: # over a month
				try: os.remove (path)
				except: self.logger.trace ()
		self.last_maintern = time.time ()
		
	def handle_spool (self, current_time):
		if self.shutdown_in_progress:
			return
		
		if self.last_maintern + 3600 >  current_time:
			self.maintern (current_time)
		
		if not self.que: # previous que has priority			
			for path in glob.glob (os.path.join (self.path_spool, "*.*")):
				try:
					fn = os.path.split (path)[-1]
					retrys, digest = fn.split (".")
					assert (len (digest) == 32)
					retrys = int (retrys)
				except (ValueError, AssertionError):
					continue
				except:
					self.logger.trace ()
					continue
						
				mtime = os.path.getmtime (path)
				if retrys > 7:
					delta = 21600
				elif retrys == 0:
					delta = 0
				else:
					delta = 4 ** retrys
				
				if retrys >= self.MAX_RETRY:
					self.que [fn] = None
				elif mtime + delta <= current_time and fn not in self.que and fn not in self.actives:
					self.que [fn] = None
		
		for i in range (self.CONCURRENTS - len (self.actives)):
			self.send ()
	
		
def usage ():
		print("""
Usage:
	smtpda.py [options...]

Options:	
	--var-path=
	--log-path=
	--verbose or -v
	--help or -h

Examples:	
	ex. smtpda.py -v
	""")


if __name__ == "__main__":
	argopt = getopt.getopt(
		sys.argv[1:], 
		"hv", 
		[
			"help", "verbose=", "log-path=", "var-path=",
			"max-retry=", "keep-days=", "server=", "user=", "password=", "ssl"
		]
	)
	_consol = "no"
	_cf = {}
	_logpath, _varpath = None, None
	for k, v in argopt [0]:
		if k == "--help" or k == "-h":
			usage ()
			sys.exit ()		
		elif k == "--verbose" or k == "-v":
			_consol = v
		elif k == "--log-path":	
			_logpath = v
		elif k == "--var-path":	
			_varpath = v
		elif k == "--max-retry":	
			_cf ['max-retry'] = int (v)
		elif k == "--keep-days":	
			_cf ['keep-days'] = int (v)	
		elif k == "--server":	
			_cf ['smtpserver'] = v
		elif k == "--user":	
			_cf ['user'] = v
		elif k == "--password":	
			_cf ['password'] = v	
		elif k == "--ssl":	
			_cf ['ssl'] = 1
		
	service = daemon.make_service (SMTPDeliverAgent, _cf, _logpath, _varpath, _consol)	
	try:
		service.run ()		
	finally:	
		if _consol not in ("1", "yes"):
			sys.stderr.close ()	
		sys.exit (lifetime._exit_code)
