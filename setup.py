"""
Hans Roh 2015 -- http://osp.skitai.com
License: BSD
"""

import skitai
__VER__ = skitai.VERSION

import sys
import os
import shutil, glob
from warnings import warn
try:
	from setuptools import setup
except ImportError:	
	from distutils.core import setup

if sys.argv[-1] == 'publish':
	if os.name == "nt":
		os.system('python setup.py sdist upload') # bdist_wininst --target-version=2.7
	else:		
		os.system('python setup.py sdist upload')
	sys.exit()

classifiers = [
  'License :: OSI Approved :: BSD License',
  'Development Status :: 4 - Beta',
  'Topic :: Internet :: WWW/HTTP',
	'Topic :: Internet :: WWW/HTTP :: HTTP Servers',				
	'Environment :: Console',
	'Environment :: No Input/Output (Daemon)',
	'Topic :: Software Development :: Libraries :: Python Modules',
	'Intended Audience :: Developers',
	'Intended Audience :: Science/Research',
	'Programming Language :: Python',
	'Programming Language :: Python :: 2.7',
	'Programming Language :: Python :: 3'
]

if "install" in sys.argv or "develop" in sys.argv:
	PY_MAJOR_VERSION = sys.version_info [0]
	if PY_MAJOR_VERSION == 3:
		if os.path.isfile ("skitai/lib/py2utils.py"):
			os.remove ("skitai/lib/py2utils.py")
			try: os.remove ("skitai/lib/py2utils.pyc")
			except OSError: pass
	else:
		if not os.path.isfile ("skitai/lib/py2utils.py"):
			with open ("skitai/lib/py2utils.py", "w") as f:
				f.write ("def reraise(type, value, tb):\n\traise type, value, tb\n")			
		
packages = [
	'skitai',
	'skitai.client',
	'skitai.dbapi',
	'skitai.lib',	
	'skitai.protocol',
	'skitai.protocol.dns',
	'skitai.protocol.dns.pydns',
	'skitai.protocol.http',	
	'skitai.requests',
	'skitai.protocol.smtp',
	'skitai.server',
	'skitai.server.dbi',
	'skitai.server.handlers',
	'skitai.server.rpc',
	'skitai.server.threads',
	'skitai.saddle'
]

package_dir = {
	'skitai': 'skitai',
	'skitai.server': 'skitai/server'
}

skitaid_files = [
	"README.md",
	"skitaid/bin/*.py",
	"skitaid/pub/default/*.py",	
	"skitaid/pub/default/static/*.*",	
	"skitaid/pub/default/templates/*.*",	
	"skitaid/etc/init/skitaid.conf",
	"skitaid/etc/init.d/skitaid", 
	"skitaid/etc/skitaid/skitaid.conf",
	"skitaid/etc/skitaid/servers-available/README.txt", 
	"skitaid/etc/skitaid/servers-enabled/default.conf",
	"skitaid/etc/skitaid/cert/*.*",
	"protocol/dns/*.txt",
	"protocol/dns/pydns/*.txt",
	"requests/*.txt",
	"tools/benchmark/*.py",
	"tools/benchmark/*.txt",
	"tools/benchmark/*.ini",
]

package_data = {
	"skitai": skitaid_files
}

with open ("README.txt") as f:
	ldesc = f.read ()

setup(
	name='skitai',
	version=__VER__,
	description='Skitai WSGI App Engine',
	long_description = ldesc,
	author='Hans Roh',
	author_email='hansroh@gmail.com',
	url='https://gitlab.com/hansroh/skitai/wikis/home',
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	license='BSD',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/skitai",
	install_requires = ["jinja2"],
	classifiers=classifiers
)

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
		except OSError as why:
			if why.errno in (17, 183): continue
			else: raise

if "install" in sys.argv or "develop" in sys.argv:
	if os.name == "nt":
		mkdir ("c:\\skitaid")
		mkdir ("c:\\skitaid\\var")
		mkdir ("c:\\skitaid\\bin")
		mkdir ("c:\\skitaid\\log")
		mkdir ("c:\\skitaid\\pub\\default\\static")
		mkdir ("c:\\skitaid\\pub\\default\\templates")
		mkdir ("c:\\skitaid\\etc\\cert")
		mkdir ("c:\\skitaid\\etc\\servers-available")
		mkdir ("c:\\skitaid\\etc\\servers-enabled")		
		
		conf = "c:\\skitaid\\etc\\skitaid.conf"
		if not os.path.isfile (conf):
			shutil.copyfile ("skitai\\skitaid\\etc\\skitaid\\skitaid.conf", conf)
		
		pathes = ["cert\\README.txt", "servers-available\\README.txt"]
		if not os.listdir ("c:\\skitaid\\etc\\servers-enabled"):
			pathes.append ("servers-enabled\\default.conf")
		for path in pathes:
			target = os.path.join ("c:\\skitaid\\etc", path)
			try: 
				os.remove (target)
			except WindowsError as why:
				if why.errno == 2: pass
			shutil.copyfile (os.path.join ("skitai\\skitaid\\etc\\skitaid", path), target)
		
		for fn in os.listdir ("skitai\\skitaid\\bin"):
			target = os.path.join ("c:\\skitaid\\bin", fn)
			try: os.remove (target)
			except WindowsError as why:
				if why.errno == 2: pass	
			shutil.copyfile (os.path.join ("skitai\\skitaid\\bin", fn), target)
		
		for fn in ("static\\index.html",):
			target = os.path.join ("c:\\skitaid\\pub\\default", fn)
			try: os.remove (target)			
			except WindowsError as why:
				if why.errno == 2: pass	
					
		for fn in ("webapp.py", "static\\reindeer.jpg", "templates\\index.html"):
			target = os.path.join ("c:\\skitaid\\pub\\default", fn)
			try: os.remove (target)
			except WindowsError as why:
				if why.errno == 2: pass	
			shutil.copyfile (os.path.join ("skitai\\skitaid\\pub\\default", fn), target)
			
		print("\n\n======================================")
		print("Installation Complete")
		print("--------------------------------------")	
		print("Please run below command in your commands prompt with administator privilege\n")
		print("  cd /d c:\\skitaid\\bin")
		print("  python install-win32-service.py --startup auto install")
		print("  python install-win32-service.py start")
		print("  then check http://localhost:5000\n\n")
	
	else:
		mkdir ("/etc/skitaid")
		mkdir ("/etc/skitaid/cert")
		mkdir ("/etc/skitaid/servers-enabled")
		mkdir ("/etc/skitaid/servers-available")
		mkdir ("/var/log/skitaid")
		mkdir ("/var/local/skitaid")		
		mkdir ("/var/local/skitaid-pub/default/static")
		mkdir ("/var/local/skitaid-pub/default/templates")
			
		conf = "/etc/skitaid/skitaid.conf"
		if not os.path.isfile (conf) and not os.path.islink (conf):
			shutil.copyfile (os.path.join ("skitai/skitaid/etc/skitaid/skitaid.conf"), "/etc/skitaid/skitaid.conf")
		
		if not os.listdir ("/etc/skitaid/servers-enabled"):
			with open ("skitai/skitaid/etc/skitaid/servers-enabled/default.conf") as f:
				data = f.read ().replace ("c:\\skitaid\\pub\default\\", "/var/local/skitaid-pub/default/")
			with open ("/etc/skitaid/servers-enabled/default.conf", "w") as f:
				f.write (data)
		
		for path in ("cert/README.txt", "servers-available/README.txt"):
			try: 
				os.remove (os.path.join ("/etc/skitaid", path))
			except OSError as why:
				if why.errno == 2: pass
			shutil.copyfile (os.path.join ("skitai/skitaid/etc/skitaid", path), os.path.join ("/etc/skitaid", path))
		
		has_py3 = os.path.isfile ("/usr/bin/python3") or os.path.islink ("/usr/bin/python3")
		for fn in ("skitaid.py", "skitaid-instance.py", "skitaid-smtpda.py"):
			target = os.path.join ("/usr/local/bin", fn)											
			with open (os.path.join ("skitai/skitaid/bin", fn), "rb") as f:
				data = f.read ()				
			with open (target, "wb") as f:			
				if has_py3:
					data = data.replace ("#!/usr/bin/python", "#!/usr/bin/python3", 1)
				f.write (data)
			os.chmod (target, 0o755)
		
		for fn in ("static/index.html",):
			target = os.path.join ("/var/local/skitaid-pub/default", fn)
			try: os.remove (target)
			except OSError as why:
				if why.errno == 2: pass
					
		for fn in ("webapp.py", "templates/index.html", "static/reindeer.jpg"):
			target = os.path.join ("/var/local/skitaid-pub/default", fn)
			try: os.remove (target)
			except OSError as why:
				if why.errno == 2: pass
			shutil.copyfile (os.path.join ("skitai/skitaid/pub/default", fn), target)
		
		if os.path.isfile ("/etc/init.d/skitaid"):
			os.remove ("/etc/init.d/skitaid")
		shutil.copyfile ("skitai/skitaid/etc/init.d/skitaid", "/etc/init.d/skitaid")
		os.chmod ("/etc/init.d/skitaid", 0o755)

		print("\n\n======================================")
		print("Installation Complete")
		print("--------------------------------------")	
		print("Please run below commands\n")
		print("  sudo service skitaid start")
		print("  wget http://localhost:5000\n\n")
		
