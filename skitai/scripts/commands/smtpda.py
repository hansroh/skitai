#!/usr/bin/python3
# 2015. 11. 27 by Hans Roh hansroh@gmail.com

import sys, os, getopt
from skitai import lifetime
from rs4 import pathtool
from ...backbone.threaded import select_trigger
from rs4.psutil import service, daemon_class
from rs4.protocols.sock.impl.smtp import async_smtp, composer
import time
import glob

DEFAULT = """[smtpda]
# SMTP Delivery Agent
max-retry = 3
keep-days = 3
smtp-server =
ssl = no
user =
password =
"""


def hTERM (signum, frame):
	lifetime.shutdown (0, 30.0)

def hHUP (signum, frame):
	lifetime.shutdown (3, 30.0)

class SMTPDeliverAgent (daemon_class.SimpleDaemonClass):
	CONCURRENTS = 2
	MAX_RETRY = 3
	UNDELIVERS_KEEP_MAX = 3600
	NAME = "smtpda"

	def __init__ (self, working_dir, config):
		self.config = config
		super ().__init__ (working_dir)
		self.que = {}
		self.actives = {}
		self.last_maintern = time.time ()
		self.shutdown_in_progress = False

	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 1:
			self.shutdown_in_progress = True

	def run (self):
		lifetime.loop (3.0)

	def setup (self):
		self.bind_signal (hTERM, hHUP)

		val = self.config.get ("max_retry", 10)
		if val: self.MAX_RETRY = val
		val = self.config.get ("keep_days", 3)
		if val: self.UNDELIVERS_KEEP_MAX = val * 3600 * 24

		if self.config.get ("smtpserver"):
			self.log ("using default SMTP: {}".format (self.config.get ("smtpserver")), "info")
		else:
			self.log ("no default SMTP server provided", "warn")

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

		self.path_spool = os.path.join (self.varpath, "spool")
		self.log ("mail spooled in {}".format (self.path_spool), "info")
		pathtool.mkdir (self.path_spool)
		composer.Composer.SAVE_PATH = self.path_spool

		self.path_undeliver = os.path.join (self.varpath, "undeliver")
		self.log ("undelivered mail saved in {}".format (self.path_undeliver), "info")
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
usage:
  skitai smtpda [options...] [start|restart|stop|status]

options:
      --help
  -d: daemonize, shortcut for <start> command
      --help
      --max-retry=<int>
      --keep-days=<int>
  -s, --smtp-server=<server_addr:port>
  -u, --user=<username>
  -p, --password=<password>
      --ssl

examples:
  ex. skitai smtpda -v
	""")
	sys.exit ()


def main ():
	argopt = getopt.getopt (
		sys.argv[1:],
		"ds:u:p:",
		[
			"help",
			"max-retry=", "keep-days=", "server=", "user=", "password=", "ssl",
			"smtp-server="
		]
	)
	_cf = {"max-retry": 5, "keep-days": 1, "ssl": 0}
	try: cmd = argopt [1][0]
	except: cmd = None
	for k, v in argopt [0]:
		if k == "--help":
			usage ()
		elif k == "-d":
			cmd = "start"
		elif k == "--max-retry":
			_cf ['max-retry'] = int (v)
		elif k == "--keep-days":
			_cf ['keep-days'] = int (v)
		elif k == "-s" or k == "--smtp-server":
			_cf ['smtpserver'] = v
		elif k == "-u" or k == "--user":
			_cf ['user'] = v
		elif k == "-p" or k == "--password":
			_cf ['password'] = v
		elif k == "--ssl":
			_cf ['ssl'] = 1

	working_dir = os.path.expanduser (f'~/.skitai/{SMTPDeliverAgent.NAME}')
	servicer = service.Service ("sktd:{}".format (SMTPDeliverAgent.NAME), working_dir)
	if cmd and not servicer.execute (cmd):
		return
	if not cmd and servicer.status (False):
		raise SystemError ("daemon is running")

	s = SMTPDeliverAgent (working_dir, _cf)
	s.start ()
	sys.exit (lifetime._exit_code)


if __name__ == "__main__":
	main ()
