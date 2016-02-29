#!/usr/bin/python
# 2016. 2. 29 by Hans Roh hansroh@gmail.com

import subprocess
import sys, os, getopt
from skitai.lib import flock, pathtool, logger, confparse
import signal
import time
import glob
import threading
from datetime import datetime


EXIT_CODE = None

def hTERM (signum, frame):			
	global EXIT_CODE
	EXIT_CODE = 0


class	CronManager:	
	def __init__ (self, config, logpath, varpath, consol):
		self.confn = config.fn
		self.logpath = logpath
		self.varpath = varpath
		self.consol = consol
		self.confmtime = 0
		self.last_maintern = 0
		self.flock = None		
		self.jobs = []
		self.currents = {}
		self.setup ()		
	
	def maintern_shutdown_request (self, now):
		global EXIT_CODE
		
		req = self.flock.lockread ("signal")
		if not req: return
		self.logger ("[info] got signal - %s" % req)
		if req in ("terminate", "shutdown"):
			EXIT_CODE = 0
		elif req == "restart":
			EXIT_CODE = 3	
		elif req == "rotate":
			try: self.logger.rotate ()
			except: self.logger.trace ()
		else:
			self.logger ("[error] unknown signal - %s" % req)
		self.flock.unlock ("signal")
	
	def close (self):
		self.logger ("[info] trying to kill childs...")
		self.maintern (time.time (), kill = True)
		self.logger ("[info] cron closed")
	
	def kill (self, pid, cmd):
		self.logger ("[info] trying to kill %s (pid: %d)" % (cmd, pid))			
		if os.name == "nt":
			import win32api, win32con, pywintypes
			try:
				handle = win32api.OpenProcess (win32con.PROCESS_TERMINATE, 0, pid)
				win32api.TerminateProcess (handle, 0)
				win32api.CloseHandle (handle)
				
			except pywintypes.error as why:
				if why.errno != 87:
					self.logger ("[error] killing %s(pid:%d) has been failed" % (cmd, pid))
					
		else:
			child.kill ()			
			
	def maintern (self, current_time, kill = False):
		for pid, (cmd, started, child) in list (self.currents.iteritems ()):			
			rcode = child.poll ()
			if rcode is None:
				if kill:
					 self.kill (pid, cmd)					 
					 del self.currents [pid]					 
				continue
			due = ((current_time - started) * 1000) - 60000
			self.logger ("[info] %s has been finished (run for %d ms, rcode is %d)" % (cmd, due, rcode))
			del self.currents [pid]
		self.last_maintern = time.time ()
							
	def run (self):
		self.logger ("[info] cron started")
		try:
			try:
				self.loop ()
			except:
				self.logger.trace ()
		finally:
			self.close ()		
	
	def parse (self, unitd, until = 60):
		if unitd == "*":
			return None
						
		try: 
			unit, interval = unitd.split ("/", 1)
		except:
			units = map (int, unitd.split (","))
		else:
			if unit == "*":
				unit = 0
			else:
				unit = int (unit)

			units = []
			for i in range (unit, until, int (interval)):
				units.append (i)
		
		# add sunday (0 or 7)
		if until == 7 and 0 in units:
			units.append (7)
			
		return units
	
	def update_jobs (self):
		mtime = os.path.getmtime (self.confn)
		
		if self.confmtime != mtime:
			self.jobs = []				
			cf = confparse.ConfParse (self.confn)
			jobs = cf.getopt ("crontab")
			if not jobs: return
			for args in jobs:
				args = args.split (" ", 5)
				if len (args) != 6:
					self.logger ("[error] invalid cron command %s" % (args,))
					continue
				
				try:
					self.jobs.append ((
						self.parse (args [0], 60),
						self.parse (args [1], 24),
						self.parse (args [2], 31),
						self.parse (args [3], 12),
						self.parse (args [4], 7),
						args [5]
					))
				
				except ValueError:
					self.logger ("[error] invalid cron command %s" % (args,))
					continue	
					
				except:
					self.logger.trace ()
					continue	
		
		now = datetime.now ().timetuple ()	
		for m, h, d, M, w, cmd in self.jobs:
			if M and now.tm_mon not in M:
				continue
			if w and now.tm_wday + 1 not in w:
				continue
			if d and now.tm_mday not in d:
				continue	
			if h and now.tm_hour not in h:
				continue
			if m and now.tm_min not in m:
				continue
			else:
				threading.Thread (target = self.execute, args = (cmd,)).start ()
				
		self.confmtime = mtime
		
	def setup (self):
		if self.consol:
			self.logger = logger.screen_logger ()
		else:
			self.logger = logger.rotate_logger (self.logpath, "cron", "daily")
		
		if os.name == "nt":
			self.flock = flock.Lock (os.path.join (self.varpath, "lock"))
			self.flock.unlockall ()
		
		if os.name != "nt":
			def hUSR1 (signum, frame):	
				self.logger.rotate ()
			
			signal.signal(signal.SIGTERM, hTERM)
			signal.signal(signal.SIGQUIT, hTERM)
		
	def execute (self, cmd):					
		self.logger ("[info] job starting: %s" % cmd)
		if os.name == "nt":
			child = subprocess.Popen (
				cmd, 
				#shell = True, if true, can't terminate process bacuase run within cmd's child
				creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
			)

		else:
			child = subprocess.Popen (
				"exec " + cmd, 
				shell = True
			)
		
		self.logger ("[info] job started (pid: %d): %s" % (child.pid, cmd))
		self.currents [child.pid] = (cmd, time.time (), child)
	
	def loop (self):
		global EXIT_CODE
		while 1:
			if EXIT_CODE is not None:
				break
			now = time.time ()	
			self.update_jobs ()
			self.maintern (now)
			for i in range (60):
				if os.name == "nt" and i % 10 == 0:
					self.maintern_shutdown_request (now)
					if EXIT_CODE is not None:
						break
				time.sleep (1)
		
		
def usage ():
		print("""
Usage:
	skitaid-cron.py [options...]

Options:
	--help or -h
	--status or -s	
	--verbose or -v

Examples:
	ex. skitaid-cron.py -v
	ex. skitaid-cron.py -s
	""")


if __name__ == "__main__":
	argopt = getopt.getopt(sys.argv[1:], "hvs", ["help", "verbose", "status"])
	_varpath = None
	_consol = False
	_status = False
	
	for k, v in argopt [0]:
		if k == "--staus" or k == "-s":
			_status = True
		elif k == "--verbose" or k == "-v":	
			_consol = True
		elif k == "--help" or k == "-h":	
			usage ()
			sys.exit ()
	
	import skitaid
	_config = skitaid.cf
	_varpath = os.path.join (skitaid.VARDIR, "daemons", "cron")
	_logpath = os.path.join (skitaid.LOGDIR, "daemons", "cron")
	if _status:
		print ("=" * 40)
		print ("Skitai Cron Status")
		print ("=" * 40)
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
	service = CronManager (_config, _logpath, _varpath, _consol)
		
	try:
		service.run ()
	finally:	
		pidlock.remove ()
		if not _consol:
			sys.stderr.close ()
		sys.exit (EXIT_CODE)
		
