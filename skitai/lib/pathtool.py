import os
import re
import urllib
import types
import sys

def mkdir (tdir, mod = -1):
	if os.path.isdir (tdir): return
	chain = [tdir]
	while 1:
		tdir, last = os.path.split (tdir)			
		if not last: break
		chain.insert (0, tdir)
	
	for dir in chain [1:]:
		try: 
			os.mkdir (dir)
			if os.name == "posix" and mod != -1: 
				os.chmod (dir, mod)
		except OSError, why:
			if why [0] in (17, 183): continue
			else: raise


def modpath (mod_name):
	if type (mod_name) is types.StringType:		
		try:
				mod = sys.modules [mod_name]
		except KeyError: 
			return "", ""		
		return mod.__name__, mod.__file__

			
NAFN = re.compile (r"[\\/:*?\"<>|]+")
def mkfn (text):
	text = urllib.unquote (text)
	return NAFN.sub ("_", text)

