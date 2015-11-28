#!/usr/bin/python
# 2014. 12. 9 by Hans Roh hansroh@gmail.com

import sys
import subprocess
import os		
import signal
import time
from skitai.lib import confparse, logger, flock, pathtool
import time

cf = confparse.ConfParse ()
if os.name == "nt":
	CONFIGPATH = r"c:\skitaid\etc"	
	SKITAI_BIN = r"c:\skitaid\bin"
	LOCKDIR = SKITAI_BIN
	
else:
	CONFIGPATH = "/etc/skitaid"
	SKITAI_BIN = r"/usr/local/bin"
	LOCKDIR = "/var/lock/skitaid"	
		
cf.read (os.path.join (CONFIGPATH, "skitaid.conf"))

PYTHON = cf.getopt ("global", "python")
if not PYTHON:
	PYTHON = "python.exe"
VARDIR = cf.getopt ("global", "var_path")
if not VARDIR:
	if os.name == "posix":
		VARDIR = "/var/local/skitaid"
	else:
		VARDIR = r"c:\skitaid\var"
			
LOGDIR = cf.getopt ("global", "log_path")
if not LOGDIR:
	if os.name == "posix":
		LOGDIR = "/var/log/skitaid"
	else:
		LOGDIR = r"c:\skitaid\log"

CONFIGDIR = os.path.join (CONFIGPATH, "servers-enabled")

LOOP = True
DIRTY_DIRS = []

class Server:
	def __init__ (self, name, logger):
		self.name = name
		self.logger = logger
		self.child = None
		self.config_path = os.path.join (CONFIGDIR, self.name + ".conf")		
		self.flock = flock.Lock (os.path.join (VARDIR, "instances", self.name, "lock"))
		self.start_time = None
		self.backoff_start_time = None
		self.backoff_interval = 5
			
	def set_backoff (self, reset = False):
		if reset:
			if self.backoff_start_time is None: 
				return
			else:		
				self.backoff_start_time = None
				self.backoff_interval = 5
				return
		
		if self.backoff_start_time is None:
			self.backoff_start_time = time.time ()
				
	def start (self):
		self.start_time = time.time ()
		if os.name == "nt":
			cmd = "%s %s --conf=%s" % (PYTHON, os.path.join (SKITAI_BIN, "skitaid-instance.py"), self.name)
		else:
			cmd = "%s --conf=%s" % (os.path.join (SKITAI_BIN, "skitaid-instance.py"), self.name)
				
		if not IS_SERVICE:
			cmd += " --verbose"
		self.logger ("[info] starting server with option: %s" % cmd)
		if os.name == "nt":
			self.child = subprocess.Popen (
				cmd, 
				shell = True,
				creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
			)
						
		else:
			self.child = subprocess.Popen (
				"exec " + cmd, 
				shell = True
			)
			
	def send_stop_signal (self):
		if self.start_time is None: return
		if os.name == "nt":
			self.flock.lock ("signal", "terminate")			
		else:
			os.kill (self.child.pid, signal.SIGTERM)


class SMTPDA (Server):
	def __init__ (self, name, logger):
		self.name = name
		self.logger = logger
		self.child = None
		self.flock = flock.Lock (os.path.join (VARDIR, "daemons", self.name, "lock"))
		self.start_time = None
		self.backoff_start_time = None
		self.backoff_interval = 5
	
	def start (self):
		self.start_time = time.time ()
		if os.name == "nt":
			cmd = "%s %s" % (PYTHON, os.path.join (SKITAI_BIN, "skitaid-smtpda.py"))
		else:
			cmd = "%s" % (os.path.join (SKITAI_BIN, "skitaid-smtpda.py"),)
				
		if not IS_SERVICE:
			cmd += " --verbose"
		self.logger ("[info] starting server with option: %s" % cmd)
		if os.name == "nt":
			self.child = subprocess.Popen (
				cmd, 
				shell = True,
				creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
			)
						
		else:
			self.child = subprocess.Popen (
				"exec " + cmd, 
				shell = True
			)
			

class Servers:
	BACKOFF_MAX_INTERVAL = 600	
	CLEAN_SHUTDOWNED = {}
	RESTART_QUEUE = {}
	DAEMONS = ("smtpda",)
	
	def __init__ (self, logger):
		self.logger = logger
		self.lock = flock.Lock (LOCKDIR)
		self.lock.unlockall ()
		self.a = {}
		self.last_slist = []
	
	def has_key (self, name):
		return name in self.a
	
	def get_servers_enabled (self):
		want_to_start = {}
		want_to_shutdown = {}
		
		slist = os.listdir (CONFIGDIR)
		for name in slist:
			if name [-5:] != ".conf": continue
			name = name [:-5]
			
			if name in self.DAEMONS:
				raise NameError ("%s is system reserved, change config name, please" % name)
				
			if name not in self.a:
				if name not in self.CLEAN_SHUTDOWNED:
					want_to_start [name] = None
					continue
				
				# move to avail, back again
				if name + ".conf" not in self.last_slist:
					want_to_start [name] = None					
					try: del self.CLEAN_SHUTDOWNED [name]
					except KeyError: pass
					
				else:
					lock = self.CLEAN_SHUTDOWNED [name]
					if lock.lockread ("signal").startswith ("restart"):
						lock.unlock ("signal")
						want_to_start [name] = None					
						try: del self.CLEAN_SHUTDOWNED [name]
						except KeyError: pass
		
		for name in self.a:
			if name not in (self.DAEMONS) and name + ".conf" not in slist:
				want_to_shutdown [name] = None				
		
		self.last_slist = slist
		return list(want_to_start.keys ()), list(want_to_shutdown.keys ())
	
	def send_signal (self, name, sig):		
		self.a [name].send_signal (sig)
		
	def stop_all (self):
		global LOOP
		LOOP = False
		for name, server in list(self.a.items ()):
			server.send_stop_signal ()

		if os.name == "posix":
			try:
				os.wait ()
			except OSError:
				pass
		
	def add_server (self, name):		
		self.a [name] = Server (name, self.logger)
		self.a [name].start ()
	
	def maintern (self):
		want_to_start, want_to_shutdown = self.get_servers_enabled ()
		#print want_to_start, want_to_shutdown
				
		for name in want_to_start:
			if name in self.a: continue
			self.logger ("[info] try starting up server `%s`" % name)
			self.add_server (name)
		
		for name in want_to_shutdown:
			if name not in self.a: continue
			self.logger ("[info] try shutdown server `%s`" % name)
			self.a [name].send_stop_signal ()
	
	def rotate (self):
		self.logger.rotate ()
	
	def start_daemons (self):			
		name = "smtpda"
		self.a [name] = SMTPDA (name, self.logger)
		self.a [name].start ()
				
	def start (self):
		self.start_daemons ()
						
		while self.a or LOOP:
			if os.name == "nt":
				sig = self.lock.lockread ("signal")
				if sig == "shutdown":
					self.logger ("[info] got skitai stop signal, try shutdown all servers")
					self.lock.unlock ("signal")
					self.stop_all ()
				elif sig == "rotate":	
					self.rotate ()
				
			self.maintern ()
			for name, server in list(self.a.items ()):				
				exitcode = server.child.poll ()
				#print name, exitcode
				if exitcode is None:
					server.set_backoff (reset = True)
					continue
				
				if exitcode == 0:
					self.logger ("[info] `%s` server has been shutdowned cleanly" % name)
					self.CLEAN_SHUTDOWNED [name] = server.flock
					del self.a [name]
					
				elif exitcode == 3:
					self.logger ("[info] try re-starting up server `%s` by admin" % name)
					self.a [name].start ()
					
				else: # unexpected error					
					server.set_backoff ()
					if time.time() - server.backoff_start_time >= server.backoff_interval:
						self.logger ("[fail] `%s` server encountered unexpected error and terminated, try re-starting up (current backoff interval is %d)" % (name, server.backoff_interval))
						server.backoff_interval = server.backoff_interval * 2
						if server.backoff_interval > self.BACKOFF_MAX_INTERVAL:
							server.backoff_interval = self.BACKOFF_MAX_INTERVAL
						self.a [name].start ()
						
			time.sleep (1)


def usage ():
	print("""
Usage:
	skitaid.py [stop|rotate] [options...]

Options:
	--verbose or -v : verbiose (default run as service)
	--name or -n [server name]
	--command or -k	[command]	
		command is one of below:
			restart
			shutdown
			terminate
			rotate
			restart-all
			shutdown-all
			terminate-all
			rotate-all

Examples:
	ex. skitaid.py : run as service
	ex. skitaid.py --verbose
	ex. skitaid.py stop
	ex. skitaid.py -k shutdown -n (server-name) 
	ex. skitaid.py -k restart-all
	""")

def _touch (req, name):
	if name.endswith (".conf"):
		name = name [:-5]
	if name in Servers.DAEMONS:
		midpath = "daemons"
	else:
		midpath = "instances"
			
	lockpath = os.path.join (VARDIR, midpath, name, "lock")
	
	if req == "start": 
		req = "restart"
	else:
		if req not in ("terminate", "shutdown", "restart", "rotate"):
			print("[error] unknown command")
			sys.exit (1)
				
	if os.name == "nt":		
		flock.Lock (lockpath).lock ("signal", req)
	else:
		pid	 = flock.PidFile (lockpath).getpid ()
		if pid is None and req == "restart":
			flock.Lock (lockpath).lock ("signal", req)
		else:
			if req == "terminate": sig = signal.SIGTERM
			elif req == "shutdown": sig = signal.SIGQUIT
			elif req == "restart": sig = signal.SIGHUP				
			elif req == "rotate": sig = signal.SIGUSR1
			os.kill (pid, sig)
	
def touch (req, name = ""):
	if name:
		return _touch (req, name)
	for each in os.listdir (CONFIGDIR):
		_touch (req, each)

	
if __name__ == "__main__":
	import getopt	
	optlist, args = getopt.getopt(
		sys.argv[1:], 
		"n:k:hv", 
		["help", "verbose", "name=", "--command"]
	)
	
	# send signal to skitai
	lck = flock.Lock (LOCKDIR)
	pidlock = lck.get_pidlock ()
	if args:
		if not pidlock.isalive ():
			print("[error] not running")
			sys.exit (1)
			
		if "stop" in args:		
			if os.name == "nt":
				lck.lock ("signal", "shutdown")
			else:
				os.kill (pidlock.getpid (), signal.SIGTERM)
			exit (0)
		
		elif "rotate" in args:		
			if os.name == "nt":
				flock.Lock (LOCKDIR).lock ("signal", "rotate")
			else:
				os.kill (pidlock.getpid (), signal.SIGUSR1)
			exit (0)	
		
		else:
			print("[error] unknown argument")
			sys.exit (1)
			
	IS_SERVICE = True
	name = ""
	command = ""
	for k, v in optlist:
		if k == "--verbose" or k == "-v":
			IS_SERVICE = False
		elif k == "--name" or k == "-n":
			name = v
		elif k == "--command" or k == "-k":
			command = v
		elif k == "--help" or k == "-h":
			usage ()
			sys.exit ()
	
	if not command and pidlock.isalive ():
		print("[error] already running")
		sys.exit (1)
	
	# send signal to sub servers
	if command:		
		if not pidlock.isalive ():
			print("[error] not running")
			sys.exit (1)
					
		if not command.endswith ("-all") and not name:
			print("[error] server name must defined. use --name or -n")
			sys.exit (1)
		
		if command.endswith ("-all"):
			command	= command [:-4]
		touch (command, name)		
		sys.exit ()
	
	l = logger.multi_logger ()
	l.add_logger (logger.rotate_logger (LOGDIR, "skitaid", "monthly"))
	
	def hTERM (signum, frame):
		ServerMamager.stop_all ()
	
	def hUSR1 (signum, frame):
		ServerMamager.rotate ()
		
	ServerMamager = Servers (l)
	if os.name == "nt":
		signal.signal(signal.SIGBREAK, hTERM)
	else:
		signal.signal(signal.SIGTERM, hTERM)
		signal.signal(signal.SIGUSR1, hUSR1)
	
	if IS_SERVICE:
		from skitai.lib import devnull
		sys.stdout = devnull.devnull ()
		sys.stderr = open (os.path.join (LOGDIR, "stderr.log"), "a")

	else:		
		l.add_logger (logger.screen_logger ())
			
	try:
		pidlock.make ()
		ServerMamager.start ()
	finally:		
		pidlock.remove ()		
		if IS_SERVICE:
			sys.stderr.close ()
		
		
