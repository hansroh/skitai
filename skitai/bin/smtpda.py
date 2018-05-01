#!/usr/bin/python3
# 2015. 11. 27 by Hans Roh hansroh@gmail.com

import sys, os, getopt
from skitai import lifetime
from aquests.lib import pathtool, logger, confparse
from aquests.lib.athreads import select_trigger
from aquests.lib.pmaster import daemon as demonizer
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
	CONCURRENTS = 2
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
		self.logger ("service %s stopped" % self.NAME)
						
	def run (self):
		self.logger ("service %s started" % self.NAME)
		try:
			try:
				lifetime.loop (3.0)
			except KeyboardInterrupt:
				pass	
			except:
				self.logger.trace ()
		finally:
			self.close ()		
	
	def setup (self):
		self.make_logger ()
		self.bind_signal (hTERM, hKILL, hHUP)
		
		val = self.config.get ("max_retry", 10)
		if val: self.MAX_RETRY = val
		val = self.config.get ("keep_days", 30)
		if val: self.UNDELIVERS_KEEP_MAX = val * 3600 * 24
		
		if self.config.get ("smtpserver"):
			self.logger ("using default SMTP: {}".format (self.config.get ("smtpserver")), "info")
		else:	
			self.logger ("no default SMTP server provided", "warn")
			
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
		
		self.path_spool = os.path.join (self.varpath, "smtpda",  "mail", "spool")
		self.logger ("mail spooled in {}".format (self.path_spool), "info")
		pathtool.mkdir (self.path_spool)
		composer.Composer.SAVE_PATH = self.path_spool
		
		self.path_undeliver = os.path.join (self.varpath, "smtpda", "mail", "undeliver")
		self.logger ("undelivered mail saved in {}".format (self.path_undeliver), "info")
		pathtool.mkdir (self.path_undeliver)
		
		lifetime.init (logger = self.logger)		
		lifetime.maintern.sched (2.0, self.handle_spool)		
		if os.name == "nt":			
			lifetime.maintern.sched (2.0, self.maintern_shutdown_request)		
		
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
	smtpda.py [options...] [start|restart|stop|status]

Options:	
	--verbose or -v
	--help or -h

Examples:	
	ex. smtpda.py -v
	""")


def main ():
	from ._makeconfig import _default_conf, _default_log_dir, _default_var_dir
	
	argopt = getopt.getopt (
		sys.argv[1:], 
		"dhv",
		[
			"help", "verbose=", "log-path=", "var-path=", "pname=",
			"max-retry=", "keep-days=", "server=", "user=", "password=", "ssl=",
			"process-display-name=", "smtp-server="
		]
	)
	
	_consol = "no"
	_cf = {"max-retry": 3, "keep-days": 3, "ssl": 0}
	_logpath, _varpath = None, None
	fileopt = []
	cf = None
	for k, v in argopt [0]:
		if k == "--var-path":
			_varpath = v			
			break
		
	if not _varpath:
		_varpath = _default_var_dir
		if os.path.isfile (_default_conf):
			cf = confparse.ConfParse (_default_conf)
			cf.setopt ("smtpda", "log-path", _default_log_dir)		
			cf.setopt ("smtpda", "process-display-name", "skitai")
			fileopt.extend (list ([("--" + k, v) for k, v in cf.getopt ("smtpda").items () if v not in ("", "false", "no")]))					
		else:
			print ("error: \n  no configuration is given \n  check ~/.skitai.conf.example or run by skitai.enable_smtpda()")
			exit (1)
					
	argopt = demonizer.handle_commandline (argopt, _varpath or _default_var_dir, "skitai")	
	for k, v in (fileopt + argopt [0]):
		if k == "--help" or k == "-h":
			usage ()
			sys.exit ()		
		elif k == "--verbose" or k == "-v":
			_consol = "yes"
		elif k == "--log-path":	
			_logpath = v
		elif k == "--var-path":	
			_varpath = v
		elif k == "--max-retry":	
			_cf ['max-retry'] = int (v)
		elif k == "--keep-days":	
			_cf ['keep-days'] = int (v)	
		elif k == "--server" or k == "--smtp-server":	
			_cf ['smtpserver'] = v
		elif k == "--user":	
			_cf ['user'] = v
		elif k == "--password":	
			_cf ['password'] = v	
		elif k == "--ssl":	
			_cf ['ssl'] = 1		
		elif k == "--pname" or k == "--process-display-name":	
			_cf ['pname'] = v
	
	service = daemon.make_service (SMTPDeliverAgent, _cf, _logpath, _varpath, _consol)
	try:
		service.run ()
	finally:	
		if _consol not in ("1", "yes", "true"):
			sys.stderr.close ()	
		sys.exit (lifetime._exit_code)


if __name__ == "__main__":
	main ()
	