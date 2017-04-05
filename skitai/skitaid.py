#!/usr/bin/python3
# 2014. 12. 9 by Hans Roh hansroh@gmail.com

__version__ = "0.8.8.1"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  __version__.split (".")))

import sys
import subprocess
import os		
import signal
import time
from aquests.lib import confparse, logger, flock, pathtool
from skitai.server.wastuff import process, daemon
import time
			
class Service (daemon.Daemon):
	BACKOFF_MAX_INTERVAL = 600
	CLEAN_SHUTDOWNED = {}
	RESTART_QUEUE = {}
	DAEMONS = ("smtpda", "cron")
	
	def __init__ (self, cmd, logpath, varpath, verbose):
		self.cmd = cmd
		self.logpath = logpath
		self.varpath = varpath
		self.consol = verbose
		self.make_logger (False)

		self.backoff_start_time = None
		self.backoff_interval = 5
		self.child = None
		self.loop = 1
	
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
	
	def shutdown (self):
		self.logger ("[info] try to kill %s..." % self.child.name)
		self.child.kill ()
		for i in range (30):
			time.sleep (1)
			if self.child.poll () is None:
				self.logger ("[info] %s is still alive" % self.child.name)				
			else:
				break
		
		if self.child.poll () is None:
			self.logger ("[info] force to kill %s" % self.child.name)
			self.child.send_signal ('kill')
	
	def hTERM (self, signum, frame):			
		self.loop = 0
		
	def run (self):
		if os.name == "nt":
			signal.signal(signal.SIGBREAK, self.hTERM)
		else:
			signal.signal(signal.SIGTERM, self.hTERM)
	
		try:
			try:
				self.start ()
			except KeyboardInterrupt:
				pass
			except:
				self.logger.trace ()
		finally:
			self.shutdown ()		
	
	def create (self):		
		self.child = process.Process (
			self.cmd, 
			'instance',
			self.varpath and self.varpath or daemon.get_default_varpath ()
		)
	
	def start (self):
		self.create ()
		try:
			while self.loop:
				exitcode = self.child.poll ()			
				if exitcode is None:
					self.set_backoff (True)
					continue
				
				if exitcode == 0:
					self.logger ("[info] instance has been shutdowned cleanly")
					break
					
				elif exitcode == 3:
					self.logger ("[info] try re-starting up instance")
					self.create ()
					
				else:
					self.set_backoff ()
					if time.time() - self.backoff_start_time >= self.backoff_interval:
						self.logger ("[fail] instance encountered unexpected error and terminated, try re-starting up (current backoff interval is %d)" % self.backoff_interval)
						self.backoff_interval = self.backoff_interval * 2
						if self.backoff_interval > self.BACKOFF_MAX_INTERVAL:
							self.backoff_interval = self.BACKOFF_MAX_INTERVAL
						self.create ()
				time.sleep (1)
		
		except KeyboardInterrupt:
			pass	

	
if __name__ == "__main__":
	service = Service ()	
	service.run ()
	