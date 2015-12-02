#!/usr/bin/python
# 2014. 12. 9 by Hans Roh hansroh@gmail.com

import sys, os, getopt
from skitai.server import Skitai
from skitai import lifetime
from skitai.lib import confparse, flock, pathtool
import signal


class	WAS (Skitai.Loader):
	def __init__ (self, config, logpath, varpath, consol):
		self.test_config (config)
		self.consol = consol
		Skitai.Loader.__init__ (self, config, logpath, varpath)		
	
	@classmethod
	def test_config (cls, conf):
		config = confparse.ConfParse (conf)
		assert (config.getint ("server", "processes") > 0)
		assert (config.getint ("server", "threads") > 0)
		if config.getopt ("server", "ssl") == "yes":
			assert (config.getopt ("server", "certfile"))
		assert (config.getint ("server", "port") > 0)
		assert (len (config.getopt ("server", "securekey")) >= 6)
		assert (len (config.getopt ("server", "admin_password")) >= 6)
		assert (config.getint ("server", "sessiontimeout") >= 0)
		
		for sect in list(config.keys ()):
			if sect.startswith ("cluster-"):
				name = sect [8:]
				assert (len (name) > 0)
				assert (config.getint (sect, "cache_timeout") >= 0)
				members = [_f for _f in [x.strip () for x in config.getopt (sect, "members").split (",")] if _f]
				assert (len (members) > 0)
				assert (config.getopt (sect, "ssl")	in ("yes", "no", None, ""))
				
	def to_list (self, text, delim = ","):
		return [_f for _f in [x.strip () for x in text.split (",")] if _f]
			
	def configure (self):
		if self.consol:
			self.wasc.logger.add_screen_logger ()
		
		# before spawn
		config = confparse.ConfParse (self.config)		
		self.wasc.register ("config", config)
		self.set_num_worker (config.getint ("server", "processes"))
		if config.getopt ("server", "ssl") in ("yes", "1") and config.getopt ("server", "certfile"):
			self.config_certification (config.getopt ("server", "certfile"), config.getopt ("server", "keyfile"))
		self.config_cachefs (os.path.join (self.varpath, "cache"))
		self.config_rcache (config.getint ("server", "num_result_cache_max"))
		self.config_session (os.path.join (self.varpath, "sessions"), config.getint ("server", "sessiontimeout"), config.getopt ("server", "securekey"))
		self.config_authorizer (config.getopt ("server", "securekey"), config.getopt ("server", "admin_password"))
		
		# spawn
		self.config_webserver (
			config.getint ("server", "port"),
			ip = config.getopt ("server", "ip"),
			name = config.getopt ("server", "name"),
			ssl = config.getopt ("server", "ssl") in ("yes", "1") or False
		)

		# after spawn
		self.config_threads (config.getint ("server", "threads"))
		
		for sect in list(config.keys ()):
			if sect.startswith ("@"):
				name = sect [1:]
				ctype = config.getopt (sect, "type")				
				members = [_f for _f in [x.strip () for x in config.getopt (sect, "members").split (",")] if _f]
				ssl = config.getopt (sect, "ssl")
				self.add_cluster (ctype, name, members, ssl)
				
		self.install_handler (config.getopt ("routes"), config.getopt ("server", "enable_proxy") == "yes",  config.getint ("server", "static_max_age"))
		
		lifetime.init ()
		
		if os.name == "nt":			
			self.flock = flock.Lock (os.path.join (self.varpath, "lock"))
			self.flock.unlockall ()
			lifetime.maintern.sched (10.0, self.maintern_shutdown_request)

	def maintern_shutdown_request (self, now):
		req = self.flock.lockread ("signal")
		if not req: return
		self.wasc.logger ("server", "[info] got signal - %s" % req)
		if req == "terminate":			
			lifetime.shutdown (0, 1)
		elif req == "restart":			
			lifetime.shutdown (3, 0)		
		elif req == "shutdown":
			lifetime.shutdown (0, 0)		
		elif req == "rotate":
			self.wasc.logger.rotate ()
		else:
			self.wasc.logger ("server", "[error] unknown signal - %s" % req)
		self.flock.unlock ("signal")



def usage ():
		print("""
Usage:
	skitaid-instance.py [options...]

Options:
	--conf or -f [ea]/yekeulus
	--verbose or -v

Examples:
	ex. skitaid-instance.py -v -f default
	ex. skitaid-instance.py -f default	
	""")


if __name__ == "__main__":
	argopt = getopt.getopt(sys.argv[1:], "f:hvt", ["help", "conf=", "verbose", "test"])
	_conf = ""
	_varpath = None
	_consol = False
	_test = False
	
	for k, v in argopt [0]:
		if k == "--conf" or k == "-f":
			_conf = v
		elif k == "--verbose" or k == "-v":	
			_consol = True
		elif k == "--test" or k == "-t":	
			_test = True	
		elif k == "--help" or k == "-h":	
			usage ()
			sys.exit ()
	
	if not _conf:
		print("[error] config is required, use --conf or -f")		
		usage ()
		sys.exit (1)
	
		
	try:
		subdir, name = _conf.split ("/", 1)
	except ValueError:
		subdir, name = 	"e", _conf
	
	if subdir == "a":
		loc = "servers-available"
	elif subdir == "e":
		loc = "servers-enabled"
	else:
		print("[error] config type is unknown, should be e or a (default: e)")		
		usage ()
		sys.exit (1)
	
	import skitaid
	_config = os.path.join (skitaid.CONFIGPATH, loc, "%s.conf" % name)
	_varpath = os.path.join (skitaid.VARDIR, "instances", name)
	_logpath = os.path.join (skitaid.LOGDIR, "instances", name)
	
	if not (os.path.isfile (_config) or os.path.islink (_config)):
		print("[error] no server config file")
		usage ()
		sys.exit (1)
	
	if _test:
		WAS.test_config (_config)
		print("[ok] config file is good")
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
	service = WAS (_config, _logpath, _varpath, _consol)
	
	try:
		service.run ()
		
	finally:	
		_exit_code = service.get_exit_code ()
		if _exit_code is not None: # master process
			pidlock.remove ()
			if not _consol:
				sys.stderr.close ()	
			sys.exit (_exit_code)
		
		else: # worker process
			sys.exit (lifetime._exit_code)
	
