import os
import subprocess, os, sys, signal, subprocess
from aquests.lib import flock

class Process:
	def __init__ (self, cmd, name, vardir = None):
		self.cmd = cmd
		self.name = name
		self.vardir = vardir		
		self.child = None
		if os.name == "nt":
			self.flock = flock.Lock (os.path.join (self.vardir, ".%s" % self.name))			
		self.create ()
	
	def create (self):	
		if os.name == "nt":
			self.child = subprocess.Popen (
				self.cmd, 
				shell = True,
				creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
			)							
		else:
			self.child = subprocess.Popen (
				"exec " + self.cmd, 
				shell = True
			)

	def send_signal (self, req):
		if req == "start": 
			req = "restart"
		else:
			if req not in ("terminate", "kill", "restart", "rotate"):
				print("[error] unknown command")
				sys.exit (1)
		
		pid	 = self.child.pid
		if os.name == "nt":		
			self.flock.lock ("signal", req)
			
			if req == "terminate":
				sig = signal.CTRL_C_EVENT
			elif req == "kill":	
				sig = signal.CTRL_BREAK_EVENT
			
			try:
				os.kill (pid, sig)
			except ProcessLookupError:
				pass	
					
		else:			
			if pid:					
				if req == "terminate": sig = signal.SIGTERM				
				elif req == "kill": sig = signal.SIGKILL
				elif req == "restart": sig = signal.SIGHUP				
				elif req == "rotate": sig = signal.SIGUSR1
				try:
					os.kill (pid, sig)
				except ProcessLookupError:
					pass
						
			elif req == "restart":
				self.flock.lock ("signal", req)
			
	def kill (self):
		self.send_signal ("terminate")
	
	def poll (self):
		return self.child.poll ()
		