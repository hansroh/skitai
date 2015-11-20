from skitai.lib import pathtool
from skitai.server import http_server

class Devnull:
	def write(self, bf): pass
	def close(self): pass
	def flush(self): pass

def update ():
	import os, time
	bladelibpath = os.path.split (os.path.split (pathtool.modpath (http_server)[-1])[0])[0]
	ups = os.path.join (bladelibpath, "blade-pending")
	if not os.path.isdir (ups): return
	today = time.strftime ("%Y%m%d%H%M%S", time.localtime (time.time ()))
	rento = os.path.join (bladelibpath, "blade-bak-%s" % today [:8])
	if os.path.isdir (rento):
		rento = os.path.join (bladelibpath, "blade-bak-%s" % today)		
	os.rename (os.path.join (bladelibpath, "blade"), rento)
	os.rename (os.path.join (bladelibpath, "blade-pending"), os.path.join (bladelibpath, "blade"))
	
def shutdown (root):
	from skitai.server import shutdown
	shutdown.shutdown (root)

def lock (root, redirect_error = 1):
	import os, sys
	from skitai.lib import pathtool
	
	pathtool.mkdir (os.path.join (root, "var/lock"))	
	if redirect_error:
		sys.stderr = open (os.path.join (root, "var/lock/error"), "a")
	
	pidfile = os.path.join (root, "var/lock/pid")
	if os.path.isfile (pidfile):
		raise AssertionError("process is runnig. terminated.")
				
	f = open (pidfile, "w")
	f.write ("%s" % os.getpid ())
	f.close ()

def unlock (root):
	import os
	pidfile = os.path.join (root, "var/lock/pid")
	if os.path.isfile (pidfile):
		os.remove (pidfile)
	
def usage ():
	print((
		"Usage:\n"
		"  %s [--root=path] [--shutdown]\n" % os.path.split (sys.argv [0])[-1]
	))

