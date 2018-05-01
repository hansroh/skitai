#!/usr/bin/python3
# 2016. 2. 29 by Hans Roh hansroh@gmail.com

import subprocess
import sys, os, getopt
from aquests.lib import pathtool, logger, confparse
from aquests.lib.pmaster import killtree, processutil
from aquests.lib.pmaster import daemon as demonizer
import signal
import time
import glob
import threading
from datetime import datetime
from skitai.server.wastuff import daemon

def hTERM (signum, frame):			
	daemon.EXIT_CODE = 0

def hHUP (signum, frame):			
	daemon.EXIT_CODE = 3

class	CronManager (daemon.Daemon):	
	NAME = "cron"
	
	def __init__ (self, config, logpath, varpath, consol):
		self.jobs = []
		self.currents = {}		
		daemon.Daemon.__init__ (self, config, logpath, varpath, consol)
		
	def close (self):
		self.logger ("trying to kill childs...")
		self.maintern (time.time (), kill = True)
		self.logger ("service cron stopped")
	
	def kill (self, pid, cmd):
		self.logger ("trying to kill pid:%d %s" % (pid, cmd))		
		if processutil.is_running (pid)	:
			killtree.kill (pid, True)
			
	def maintern (self, current_time, kill = False):
		for pid, (cmd, started, child) in list (self.currents.items ()):			
			rcode = child.poll ()
			due = ((current_time - started) * 1000)
			
			if due > 60000:
				due -= 60000				
			if due > 120000:
				due = "%2.1f min" % (due / 1000. / 60.,)
			elif due > 1000:
				due = "%2.1f sec" % (due / 1000.,)
			else:
				due = "%d ms" % due				
			
			if rcode is None:
				if kill:
					 self.kill (pid, cmd)					 
					 del self.currents [pid]					 
				else:
					self.logger ("job still running pid:%d for %s, %s" % (pid, due, cmd))
				continue
			
			self.logger ("job has been finished pid:%d with rcode:%d for %s, %s" % (pid, rcode, due, cmd))
			del self.currents [pid]
		self.last_maintern = time.time ()

	def run (self):
		self.logger ("service cron started")
		try:
			try:
				self.loop ()
			except KeyboardInterrupt:
				pass
			except:
				self.logger.trace ()
		finally:
			self.close ()		
	
	def parse (self, unitd, umax = 60):
		#print ("---", unitd)
		
		if unitd == "*":
			return []
						
		try: 
			unit, interval = unitd.split ("/", 1)
		except ValueError:
			unit, interval = unitd, 0
		else:
			interval = int (interval)
			if interval == 1 and unit in "0*":
				return []			
			if unit == "*":
				unit = "0"								
			if interval > umax / 2.:
				raise ValueError ("interval %d is too big" % interval)
		
		units = {}
		_all = unit.split (",")
		_all_len = len (_all)
		
		for subunit in _all:
			if subunit.find ("-") == -1:
				if interval == 0 or _all_len > 1:
					units [int (subunit)] = None
				else:	
					for i in range (int (subunit), umax, interval):
						units [i] = None
						
			else:
				a, b = subunit.split ("-", 1)
				if a == "":
					a = 0
				else:
					a = int (a)
				if b == "":
					b = umax			
				else:	
					b = int (b) + 1
				for i in range (a, b, interval == 0 and 1 or interval):
					units [i] = None
		
		# add sunday (0 or 7)
		if umax == 7 and 0 in units:
			del units [0]
			units [7] = None
			
		r = list (units.keys ())
		r.sort ()
		return r
	
	def update_jobs (self, jobs):			
		self.jobs = []				
		
		if not jobs: return
		for job in jobs:
			args = job.split (" ", 5)
			if len (args) != 6:
				self.logger ("invalid cron command %s" % (args,), "error")
				continue
			
			try:
				sched = (
					self.parse (args [0], 60),
					self.parse (args [1], 24),
					self.parse (args [2], 31),
					self.parse (args [3], 12),
					self.parse (args [4], 7),
					args [5]
				)					
			
			except ValueError as why:
				self.logger ("%s, %s" % (job, why), "error")
				continue	
				
			except:
				self.logger.trace (job)
				continue	
			
			else:
				self.jobs.append (sched)
				self.logger ("job added %s" % job)
	
	def check_sched_per_minute (self):				
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
		
	def setup (self):
		self.make_logger ()
		self.bind_signal (hTERM, hTERM, hHUP)		
		self.update_jobs (self.config.get ('jobs', []))
		
	def execute (self, cmd):					
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
		
		self.logger ("job started with pid:%d %s" % (child.pid, cmd))
		self.currents [child.pid] = (cmd, time.time (), child)
	
	def loop (self):
		while 1:
			if daemon.EXIT_CODE is not None:
				break				
			now = time.time ()			
			self.maintern (now)
			self.check_sched_per_minute ()
			for i in range (60):
				if os.name == "nt" and i % 10 == 0:
					self.maintern_shutdown_request (now)
				if daemon.EXIT_CODE is not None:
					break
				time.sleep (1)
		

def usage ():
		print("""
Usage:
	cron.py [options...] [start|restart|stop|status] [jobs...]

Options:
	--verbose or -v
	--help or -h

Examples:
	ex. cron.py -v	
	""")


def main ():
	from ._makeconfig import _default_conf, _default_log_dir, _default_var_dir
	
	argopt = getopt.getopt (
		sys.argv[1:], 
		"dhv",
		[
			"help", "verbose=", "log-path=", "var-path=", 
			"pname=", "process-display-name="
		]
	)
	
	_consol = "no"
	_cf = {}
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
			if not	cf.has_key ("cron"):		
				cf.setsect ("cron", {})
			cf.setopt ("cron", "log-path", _default_log_dir)
			cf.setopt ("cron", "process-display-name", "skitai")
			fileopt.extend (list ([("--" + k, v) for k, v in cf.getopt ("cron").items () if v not in ("", "false", "no")]))			 
		else:
			print ("error: \n  no configuration is given \n  check ~/.skitai.conf.example or run by skitai.cron()")
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
		elif k == "--pname" or k == "--process-display-name":	
			_cf ["pname"] = v
			
	_cf ["conffile"] = _default_conf
	_cf ['jobs'] = []
	for job in (cf and cf.getopt ("crontab") or [] + argopt [1]):
		_cf ['jobs'].append (job)
		
	service = daemon.make_service (CronManager, _cf, _logpath, _varpath, _consol)	
	try:
		service.run ()
	finally:	
		if _consol not in ("1", "yes", "true"):
			sys.stderr.close ()
		sys.exit (daemon.EXIT_CODE)

if __name__ == "__main__":
	main ()


		