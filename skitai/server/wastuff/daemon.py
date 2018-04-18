from skitai import lifetime
from aquests.lib import pathtool, logger
import os, signal, sys, tempfile
from aquests.lib.pmaster.processutil import set_process_name
from aquests.lib.pmaster import flock
import skitai
import time, sys, os
from _ast import arg
import getpass
from hashlib import md5

EXIT_CODE = None

class Daemon:
	NAME = "base"
	def __init__ (self, config, logpath, varpath, consol):
		self.config = config
		self.logpath = logpath
		self.varpath = varpath
		self.consol = consol
		self.last_maintern = 0
		self.flock = None
		self.shutdown_in_progress = False	
		self.handlers = {}	
		set_process_name ("%s: %s" % (config.get ("pname") or skitai.get_proc_title (), self.NAME))
		self.setup ()
		
	def maintern_shutdown_request (self, now):
		# for wind32 only, scheduled call by lifetime
		global EXIT_CODE
		
		req = self.flock.lockread ("signal")
		if not req: return
		self.logger ("%s: got signal - %s" % (self.NAME, req))
		if req in ("terminate", "kill"):
			EXIT_CODE = 0
		elif req == "restart":
			EXIT_CODE = 3	
		elif req == "rotate":
			try: self.logger.rotate ()
			except: self.logger.trace ()
		else:
			self.logger ("%s: unknown signal - %s" % (self.NAME, req), "error")
		self.flock.unlock ("signal")
		
		if EXIT_CODE is not None:
			self.handlers [req](None, None)
		
	def make_logger (self, create_flock = True):		
		self.logger = logger.multi_logger ()
		if self.consol:
			self.logger.add_logger (logger.screen_logger ())
		if self.logpath:
			self.logger.add_logger (logger.rotate_logger (self.logpath, self.NAME, "weekly"))
			self.logger ("{} log path: {}".format (self.NAME, self.logpath), "info")		
		if create_flock and os.name == "nt":			
			self.flock = flock.Lock (os.path.join (self.varpath, "%s" % self.NAME))
			self.flock.unlockall ()
		self.logger ("{} tmp path: {}".format (self.NAME, self.varpath), "info")
			
	def bind_signal (self, term, kill, hup):
		self.handlers ["terminate"] = term
		self.handlers ["kill"] = kill
		self.handlers ["restart"] = hup
		
		if os.name == "nt":
			signal.signal(signal.SIGBREAK, term)
		else:	
			def hUSR1 (signum, frame):	
				self.logger.rotate ()			
			
			signal.signal(signal.SIGUSR1, hUSR1)
			signal.signal(signal.SIGTERM, term)
			#signal.signal(signal.SIGKILL, kill)
			signal.signal(signal.SIGHUP, hup)
			
	def setup (self):
		raise NotImplementedError


def get_base_tmp (fullpath):
	fullpath = os.path.abspath (fullpath or os.path.join (os.getcwd (), sys.argv [0]))
	return '%s/%s' % (getpass.getuser(), md5 (fullpath.encode ('utf8')).hexdigest () [:16])
	 	
def get_default_varpath (fullpath = None):	
	tmp = get_base_tmp (fullpath)
	return os.name == "posix" and '/var/tmp/skitai/%s' % tmp or os.path.join (tempfile.gettempdir(), tmp)

def get_default_logpath (fullpath = None):	
	tmp = get_base_tmp (fullpath)	
	return os.name == "posix" and '/var/log/skitai/%s' % tmp or os.path.join (tempfile.gettempdir(), tmp)

def make_service (service_class, config, logpath, varpath, consol):
	if logpath:
		pathtool.mkdir (logpath)
	if not varpath:	
		varpath = get_default_varpath ()		
	pathtool.mkdir (varpath)	
	
	lck = flock.Lock (os.path.join (varpath, "%s" % service_class.NAME))
	pidlock = lck.get_pidlock ()
	if pidlock.isalive ():
		print("[error] already running")
		sys.exit (0)
	
	if consol not in ("1", "yes"): # service mode
		from aquests.lib import devnull		
		sys.stdout = devnull.devnull ()		
		sys.stderr = open (os.path.join (varpath, "stderr.%s" % service_class.NAME), "a")
		
	return service_class (config, logpath, varpath, consol)


