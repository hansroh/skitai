import os
import re
try:
	import urllib.parse
	unquote = urllib.parse.unquote
except ImportError:
	import urlparse
	unquote = urlparse.unquote
		
import types
import sys

def mkdir (tdir, mod = -1):
	while tdir:
		if tdir [-1] in ("\\/"):
			tdir = tdir [:-1]
		else:
			break	

	if os.path.isdir (tdir): return	
	chain = [tdir]	
	while 1:
		tdir, last = os.path.split (tdir)		
		if not last: 
			break
		if tdir:
			chain.insert (0, tdir)
	
	for dir in chain [1:]:
		try: 
			os.mkdir (dir)
			if os.name == "posix" and mod != -1:
				os.chmod (dir, mod)				
		except OSError as why:
			if why.errno in (17, 183): continue
			else: raise


def modpath (mod_name):	
	if type (mod_name) in (str, bytes):		
		try:
				mod = sys.modules [mod_name]
		except KeyError: 
			return "", ""		
		return mod.__name__, mod.__file__

			
NAFN = re.compile (r"[\\/:*?\"<>|]+")
def mkfn (text):
	text = unquote (text)
	return NAFN.sub ("_", text)

