#!/usr/bin/python
# 2014. 12. 9 by Hans Roh hansroh@gmail.com

import sys, os, getopt
from skitai import lifetime
from skitai.lib import flock, pathtool, logger
from skitai.protocol.smtp import async_smtp, composer
import signal
import time

def hTERM (signum, frame):			
	lifetime.shutdown (0, 1)

def hQUIT (signum, frame):			
	lifetime.shutdown (0, 0)

def hHUP (signum, frame):			
	lifetime.shutdown (3, 0)

	
class	SMTPDeliverAgent:
	def __init__ (self, config, logpath, varpath, consol):
		self.consol = consol
		self.config = config
		self.logpath = logpath
		self.varpath = varpath
		
		self.que = {}
		self.actives = {}
		self.flock = None
		self.shutdown_in_progress = False
		
		self.setup ()
	
	def maintern_shutdown_request (self, now):
		req = self.flock.lockread ("signal")
		if not req: return
		self.wasc.logger ("server", "[info] got signal - %s" % req)
		if req == "terminate":			
			lifetime.shutdown (0, 1)
		elif req == "restart":			
			lifetime.shutdown (3, 0)		
		elif req == "shutdown":
			lifetime.shutdown (0, 0)		
		elif req == "rotate":
			self.logger.rotate ()
		else:
			self.logger ("[error] unknown signal - %s" % req)
		self.flock.unlock ("signal")
	
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 1:
			self.shutdown_in_progress = True
	
	def close (self):
		pass
						
	def run (self):
		try:
			try:
				lifetime.loop (3.0)
			except:
				self.logger.trace ()
		finally:
			self.close ()		
					
	def setup (self):
		self.path_spool = os.path.join (self.varpath, "mail", "spool")
		pathtool.mkdir (self.path_spool)
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
		while self.que:		
			fn = self.que.popitem () [0]
			if fn in self.actives: continue
			self.actives [fn] = time.time ()
			path = os.path.join (self.path_spool, fn)
			cmps = composer.load (path)
			if cmps.get_SLL ():
				request = async_smtp.SMTP_SLL
			else:	
				request = async_smtp.SMTP			
			request (cmps, self.logger, self.when_done)					
			break
	
	def when_done (self, code, reps, cmps):
		fn = cmps.get_FILENAME ()
		if code == -250:
			cmps.remove ()
		else:
			if cmps.get_RETRYS () > 10:				
				cmps.moveto (self.path_undeliver)
			else:	
				cmps.moveto (self.path_spool)		
		del self.actives [fn]
		
		if self.shutdown_in_progress:
			return
		
		self.send ()
	
	def handle_spool (self):
		if self.shutdown_in_progress:
			return
		
		current_time - time.time ()
		self.que = []
		for path in glob.glob (os.path.join (self.path_spool, "*.*")):
			try:
				retrys, fn = os.path.split (path)[-1].split (".")
				assert (len (fn) == 32)
				retrys = int (retrys)
			except (ValueError, AssertionError):
				continue
				
			ctime = os.get_ctime (path)
			if retrys > 7:
				delta = 21600
			else:
				delta = 4 ** retrys					
			if ctime + delta >= current_time and fn not in self.que and fn not in self.actives:
				self.que [fn] = None
		
		for i in range (4 - len (self.actives)):
			self.send ()
	

		
def usage ():
		print("""
Usage:
	skitaid-smtpda.py [options...]

Options:
	--conf or -f [ea]/yekeulus
	--verbose or -v

Examples:
	ex. skitaid-smtpda.py -v -f default
	ex. skitaid-smtpda.py -f default	
	""")


if __name__ == "__main__":
	argopt = getopt.getopt(sys.argv[1:], "hvs", ["help", "verbose", "status"])
	_varpath = None
	_consol = False
	
	for k, v in argopt [0]:
		if k == "--staus" or k == "-s":
			_conf = v
		elif k == "--verbose" or k == "-v":	
			_consol = True
		elif k == "--help" or k == "-h":	
			usage ()
			sys.exit ()
	
	import skitaid
	_config = skitaid.cf
	_varpath = os.path.join (skitaid.VARDIR, "daemons", "smtpda")
	_logpath = os.path.join (skitaid.LOGDIR, "daemons", "smtpda")
		
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
	service = SMTPDeliverAgent ()
		
	try:
		service.run ()		
	finally:	
		pidlock.remove ()
		if not _consol:
			sys.etderr.close ()	
		sys.exit (lifetime._exit_code)
		
		