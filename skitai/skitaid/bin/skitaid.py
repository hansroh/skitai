#!/usr/bin/python
# 2014. 12. 9 by Hans Roh hansroh@gmail.com

import sys
import subprocess
import os		
import signal
import time
from skitai.lib import confparse, logger, flock, pathtool
import time


def printlog (path):
	if not os.path.isfile (path):
		print ("- log file not found\n- %s" % path)
		
	import codecs
	size = os.path.getsize (path)
	with codecs.open (path, "r") as f:
		p = size - 16384
		if p < -1:
			p = 0
		f.seek (p)
		data = f.read ()		
	print ("..." + data)	
	if p:
		print ("\n- displayed last 16Kb of %dKb" % (size/1024.,))
	else:
		print ("\n- displayed all of %dKb" % (size/1024.,))	
	print ("- %s" % path)	
	
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
	
	def get_cmd (self):
		if os.name == "nt":
			return "%s %s" % (PYTHON, os.path.join (SKITAI_BIN, "skitaid-smtpda.py"))
		else:
			return "%s" % (os.path.join (SKITAI_BIN, "skitaid-smtpda.py"),)		
	
	def start (self):
		self.start_time = time.time ()
		cmd = self.get_cmd ()
				
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
			

class Cron (SMTPDA):	
	def get_cmd (self):
		if os.name == "nt":
			return "%s %s" % (PYTHON, os.path.join (SKITAI_BIN, "skitaid-cron.py"))
		else:
			return "%s" % (os.path.join (SKITAI_BIN, "skitaid-cron.py"),)
	
			
class Servers:
	BACKOFF_MAX_INTERVAL = 600
	CLEAN_SHUTDOWNED = {}
	RESTART_QUEUE = {}
	DAEMONS = ("smtpda", "cron")
	
	def __init__ (self, logger):
		self.logger = logger
		self.lock = flock.Lock (LOCKDIR)
		self.lock.unlockall ()
		self.a = {}
		self.req_stop_all = False
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
		if self.req_stop_all:
			return
		
		self.req_stop_all = True			
		LOOP = False
		childs = []
		for name, server in list(self.a.items ()):
			childs.append (server.child)
			server.send_stop_signal ()
		
		while 1:
			veto = False
			for child in childs:
				veto = (server.child.poll () == None)
				if veto:
					time.sleep (1)
					break
										
			if not veto:
				break
			
	def add_server (self, name):		
		self.a [name] = Server (name, self.logger)
		self.a [name].start ()
	
	def maintern (self):
		global LOOP
		
		want_to_start, want_to_shutdown = self.get_servers_enabled ()
		#print want_to_start, want_to_shutdown
		
		for name in want_to_start:
			if not LOOP: 
				try: del self.a [name]
				except KeyError: continue	
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
		
		name = "cron"
		self.a [name] = Cron (name, self.logger)
		self.a [name].start ()
	
	def run (self):
		try:
			try:
				self.start ()
			except:
				self.logger.trace ()	
		finally:
			self.stop_all ()
		
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
				#print (name, exitcode)
				if exitcode is None:
					server.set_backoff (reset = True)
					continue
				
				if exitcode == 0:
					self.logger ("[info] `%s` server has been shutdowned cleanly" % name)
					self.CLEAN_SHUTDOWNED [name] = server.flock
					del self.a [name]
					
				elif exitcode == 3:
					if not LOOP:
						try: del self.a [name]
						except KeyError: pass	
						continue						
					self.logger ("[info] try re-starting up server `%s` by admin" % name)
					self.a [name].start ()
					
				else:
					if not LOOP:
						try: del self.a [name]
						except KeyError: pass	
						continue
						# unexpected error
						
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
	skitaid.py [options...] [command]

Options:
	--verbose or -v : verbose mode (default run as service)
	--config or -f [config file name without .conf | smtpda | cron ]
	--log-suffix or -s [log file suffix]
		
Command:
	if -f or --config is given:
	  [ restart | shutown | terminate | roate | log ]
	  
	else:
	  skitaid.py control commands
	    [ start | stop | log | rotate ]
	    if command is not given, assumed 'start'
	    
	  command for all skitaid instances except smtpda and cron daemons
	    [ restart-all | shutown-all | terminate-all | roate-all ]

Examples:
	ex. skitaid.py
	ex. skitaid.py --verbose
	ex. skitaid.py stop
	ex. skitaid.py -f sample shutdown
	ex. skitaid.py restart-all
	ex. skitaid.py -f cron log
	ex. skitaid.py -f sample -s request log
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
		pid	 = flock.PidFile (lockpath).getpid ("skitaid")
		if pid is None:
			if req == "restart":
				flock.Lock (lockpath).lock ("signal", req)
			else:
				print("[error] no such instance '%s'" % name)
				sys.exit (1)
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
		"f:n:hvls:", 
		["help", "verbose", "name=", "config=", "log-suffix="]
	)
	
	# send signal to skitai
	lck = flock.Lock (LOCKDIR)
	pidlock = lck.get_pidlock ()
	
	IS_SERVICE = True
	name = ""
	suffix = "app"
	for k, v in optlist:
		if k == "--verbose" or k == "-v":
			IS_SERVICE = False
		elif k == "--config" or k == "-f" or k == "--name" or k == "-n":
			name = v		
		elif k == "--log-suffix" or k == "-s":	
			suffix = v
		elif k == "--help" or k == "-h":
			usage ()
			sys.exit ()
	
	try:
		command = args [0]
	except IndexError:
		command = ""		
	
	if name or (not name and command.endswith ("-all")):
		if command == "log":
			if not name:
				print("[error] for displaying logs, need instance name" % name)
				sys.exit (1)
			
			if name in ("smtpda", "cron"):
				printlog (os.path.join (LOGDIR, "daemons", name, "%s.log" % name))
			else:				
				printlog (os.path.join (LOGDIR, "instances", name, "%s.log" % suffix))
			sys.exit (0)
			
		if not pidlock.isalive ():
			print("[error] skitaid not running")
			sys.exit (1)
			
		if not command:		
			print("[error] command required for %s instance" % name)
			sys.exit (1)
		
		# send signal to sub servers
		else:
			if command.endswith ("-all"):
				if name:
					print("[error] cannot run with -f or --config")
					sys.exit (1)
					
				command	= command [:-4]
			touch (command, name)		
			sys.exit ()
		
	else:
		if command == "":
			command = "start"
		
		if command != "start":
			if command == "log":		
				printlog (os.path.join (LOGDIR, "skitaid.log"))
				sys.exit (0)
				
			if not pidlock.isalive ():
				print("[error] skitaid not running")
				sys.exit (1)
				
			elif command == "stop":		
				if os.name == "nt":
					lck.lock ("signal", "shutdown")
				else:
					os.kill (pidlock.getpid (), signal.SIGTERM)
				exit (0)
			
			elif command == "rotate":		
				if os.name == "nt":
					flock.Lock (LOCKDIR).lock ("signal", "rotate")
				else:
					os.kill (pidlock.getpid (), signal.SIGUSR1)
				exit (0)	
			
			else:
				print("[error] unknown command '%s'" % command)
				sys.exit (1)
		
		else:
			if pidlock.isalive ():
				print("[error] skitaid already running")
				sys.exit (1)
				
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
				ServerMamager.run ()
			finally:
				pidlock.remove ()		
				if IS_SERVICE:
					sys.stderr.close ()
		
		
