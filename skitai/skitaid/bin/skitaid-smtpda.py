#!/usr/bin/python
# 2015. 11. 27 by Hans Roh hansroh@gmail.com

import sys, os, getopt
from skitai import lifetime
from skitai.lib import flock, pathtool, logger
from skitai.server.threads import select_trigger
from skitai.protocol.smtp import async_smtp, composer
import signal
import time
import glob

def hTERM (signum, frame):			
	lifetime.shutdown (0, 1)

def hQUIT (signum, frame):			
	lifetime.shutdown (0, 0)

def hHUP (signum, frame):			
	lifetime.shutdown (3, 0)


class	SMTPDeliverAgent:
	CONCURRENTS = 4
	MAX_RETRY = 10
	UNDELIVERS_KEEP_MAX = 2592000

	def __init__ (self, config, logpath, varpath, consol):
		self.config = config
		self.logpath = logpath
		self.varpath = varpath
		self.consol = consol
		self.last_maintern = 0
		self.que = {}
		self.actives = {}
		self.flock = None
		self.shutdown_in_progress = False
		
		self.setup ()
	
	def maintern_shutdown_request (self, now):
		req = self.flock.lockread ("signal")
		if not req: return
		self.logger ("[info] got signal - %s" % req)
		if req == "terminate":			
			lifetime.shutdown (0, 1)
		elif req == "restart":			
			lifetime.shutdown (3, 0)		
		elif req == "shutdown":
			lifetime.shutdown (0, 0)		
		elif req == "rotate":
			try: self.logger.rotate ()
			except: self.logger.trace ()
		else:
			self.logger ("[error] unknown signal - %s" % req)
		self.flock.unlock ("signal")
	
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 1:
			self.shutdown_in_progress = True
	
	def close (self):
		self.logger ("[info] service smtpda stopped")
						
	def run (self):
		self.logger ("[info] service smtpda started")
		try:
			try:
				lifetime.loop (3.0)
			except:
				self.logger.trace ()
		finally:
			self.close ()		
					
	def setup (self):
		val = self.config.getint ("smtpda", "max_retry", 10)
		if val: self.MAX_RETRY = val
		val = self.config.getint ("smtpda", "undelivers_keep_max_days", 30)
		if val: self.UNDELIVERS_KEEP_MAX = val * 3600 * 24

		self.default_smtp = (
			self.config.getopt ("smtpda", "smtpserver"),
			self.config.getopt ("smtpda", "user"),
			self.config.getopt ("smtpda", "password"),
			self.config.getopt ("smtpda", "ssl") in ("1", "yes") and True or False
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
		
		if self.consol:
			self.logger = logger.screen_logger ()
		else:
			self.logger = logger.rotate_logger (self.logpath, "smtpda", "daily")
		
		lifetime.init ()		
		lifetime.maintern.sched (3.0, self.handle_spool)
		if os.name == "nt":
			self.flock = flock.Lock (os.path.join (self.varpath, "lock"))
			self.flock.unlockall ()
			lifetime.maintern.sched (10.0, self.maintern_shutdown_request)
		
		if os.name != "nt":
			def hUSR1 (signum, frame):	
				self.logger.rotate ()	
			
			signal.signal(signal.SIGUSR1, hUSR1)
			signal.signal(signal.SIGHUP, hHUP)
			signal.signal(signal.SIGTERM, hTERM)
			signal.signal(signal.SIGQUIT, hQUIT)		
	
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
	skitaid-smtpda.py [options...]

Options:
	--log or -l: print log
	--verbose or -v
	--help or -h

Examples:
	ex. skitaid-smtpda.py -l
	ex. skitaid-smtpda.py -v
	""")


if __name__ == "__main__":
	argopt = getopt.getopt(sys.argv[1:], "hvl", ["help", "verbose", "log"])
	_varpath = None
	_consol = False
	_log = False
	
	for k, v in argopt [0]:
		if k == "--log" or k == "-l":
			_log = True
		elif k == "--verbose" or k == "-v":	
			_consol = True
		elif k == "--help" or k == "-h":	
			usage ()
			sys.exit ()
	
	import skitaid
	_config = skitaid.cf
	_varpath = os.path.join (skitaid.VARDIR, "daemons", "smtpda")
	_logpath = os.path.join (skitaid.LOGDIR, "daemons", "smtpda")
	
	if _log:		
		skitaid.printlog (os.path.join (_logpath, "smtpda.log"))
		sys.exit (0)
		
	lck = flock.Lock (os.path.join (_varpath, "lock"))
	pidlock = lck.get_pidlock ()
	
	if pidlock.isalive ():
		print("[error] already running")
		sys.exit (1)
	
	pathtool.mkdir (_logpath)
	if not _consol: # service mode
		from skitai.lib import devnull		
		sys.stdout = devnull.devnull ()		
		sys.stderr = open (os.path.join (_logpath, "stderr.log"), "a")
	
	pidlock.make ()
	service = SMTPDeliverAgent (_config, _logpath, _varpath, _consol)
		
	try:
		service.run ()		
	finally:	
		pidlock.remove ()
		if not _consol:
			sys.stderr.close ()	
		sys.exit (lifetime._exit_code)
		
