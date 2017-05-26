from skitai import lifetime
from aquests.lib import flock, pathtool, logger
import os, signal, sys, tempfile

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
		self.setup ()
	
	def maintern_shutdown_request (self, now):
		global EXIT_CODE
		
		req = self.flock.lockread ("signal")
		if not req: return
		self.logger ("[info] got signal - %s" % req)
		if req in ("terminate", "kill"):
			EXIT_CODE = 0
		elif req == "restart":
			EXIT_CODE = 3	
		elif req == "rotate":
			try: self.logger.rotate ()
			except: self.logger.trace ()
		else:
			self.logger ("[error] unknown signal - %s" % req)
		self.flock.unlock ("signal")
		return req
	
	def make_logger (self, create_flock = True):
		self.logger = logger.multi_logger ()
		if self.consol:
			self.logger.add_logger (logger.screen_logger ())
		if self.logpath:
			self.logger.add_logger (logger.rotate_logger (self.logpath, self.NAME, "daily"))
		if create_flock and os.name == "nt":			
			self.flock = flock.Lock (os.path.join (self.varpath, ".%s" % self.NAME))
			self.flock.unlockall ()
			
	def bind_signal (self, term, kill, hup):		
		if os.name == "nt":
			signal.signal(signal.SIGBREAK, term)
		else:	
			def hUSR1 (signum, frame):	
				self.logger.rotate ()			
			signal.signal(signal.SIGTERM, term)
			#signal.signal(signal.SIGKILL, kill)
			signal.signal(signal.SIGHUP, hup)
			signal.signal(signal.SIGUSR1, hUSR1)
	
	def setup (self):
		raise NotImplementedError
					
def get_default_varpath ():
	fullpath = os.path.join (os.getcwd (), sys.argv [0])
	script = os.path.split (fullpath)[-1]
	if script.endswith (".py"):
		script = script [:-3]	
	_var = 'skitai-%s-%s' % (script, abs (hash (fullpath) & 0xffffffff))
	return os.name == "posix" and '/var/tmp/%s' % _var or os.path.join (tempfile.gettempdir(), _var)

def make_service (service_class, config, logpath, varpath, consol):
	if logpath:
		pathtool.mkdir (logpath)
	if not varpath:	
		varpath = get_default_varpath ()		
	pathtool.mkdir (varpath)	
	
	lck = flock.Lock (os.path.join (varpath, ".%s" % service_class.NAME))
	pidlock = lck.get_pidlock ()
	if pidlock.isalive ():
		print("[error] already running")
		sys.exit (0)
	
	if consol not in ("1", "yes"): # service mode
		from aquests.lib import devnull		
		sys.stdout = devnull.devnull ()		
		sys.stderr = open (os.path.join (logpath, "stderr-%s.log" % service_class.NAME), "a")
	
	return service_class (config, logpath, varpath, consol)
