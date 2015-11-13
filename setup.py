"""
Hans Roh 2015 -- http://sae.skitai.com
License: BSD
"""

__VER__ = '0.9.3.1'

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
		os.system('python setup.py sdist bdist_wininst --target-version=2.7 upload') # bdist_wininst
	else:		
		os.system('python setup.py sdist upload')
	sys.exit()

if sys.version_info < (2, 7, 0) or sys.version_info >= (3, 0, 0):
	warn("Skitai tested only in 2.7")
	sys.exit()

classifiers = [
  'License :: OSI Approved :: BSD License',
  "Development Status :: 3 - Alpha",
  'Topic :: Internet :: WWW/HTTP',
	'Topic :: Internet :: WWW/HTTP :: HTTP Servers',				
	'Environment :: Console',
	'Environment :: No Input/Output (Daemon)',
	'Topic :: Software Development :: Libraries :: Python Modules',
	'Intended Audience :: Developers',
	'Intended Audience :: Science/Research',
	'Programming Language :: Python',
	'Programming Language :: Python :: 2.7'
]
    
packages = [
	'skitai',
	'skitai.client',
	'skitai.dbapi',
	'skitai.lib',	
	'skitai.protocol',
	'skitai.protocol.dns',
	'skitai.protocol.http',	
	'skitai.server',
	'skitai.server.dbi',
	'skitai.server.handlers',
	'skitai.server.rpc',
	'skitai.server.threads'
]

package_dir = {
	'skitai': 'skitai',
	'skitai.server': 'skitai/server'
}

skitaid_files = [
	"README.md",
	"skitaid/bin/*.*",	
	"skitaid/pub/default/*.py",	
	"skitaid/pub/default/static/*.*",	
	"skitaid/etc/init/skitaid.conf",
	"skitaid/etc/init.d/skitaid", 
	"skitaid/etc/skitaid/skitaid.conf",
	"skitaid/etc/skitaid/servers-available/README.TXT", 
	"skitaid/etc/skitaid/servers-enabled/default.conf",
	"skitaid/etc/skitaid/cert/generate/*.*"
]

package_data = {
	"skitai": skitaid_files
}

#required = ["jinja2", "jsonrpclib", "m2crypto", "psycopg2"]
required = ["jinja2", "jsonrpclib"]

with open ("README.txt") as f:
	ldesc = f.read ()

setup(
	name='skitai',
	version=__VER__,
	description='Skitai App Engine',
	long_description = ldesc,
	author='Hans Roh',
	author_email='hansroh@gmail.com',
	url='https://gitlab.com/hansroh/skitai/wikis/home',
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	install_requires=required,
	license='BSD',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/skitai",
	classifiers=classifiers
)

if "install" in sys.argv or "develop" in sys.argv:
	if os.name == "nt":
		if not os.path.isdir ("c:\\skitaid"):
			shutil.copytree ("skitai\\skitaid\\etc\\skitaid", "c:\\skitaid\\etc")
			os.mkdir ("c:\\skitaid")
			os.mkdir ("c:\\skitaid\\var")
			os.mkdir ("c:\\skitaid\\log")
		
		if os.path.isdir ("c:\\skitaid\\bin"):
			for each in glob.glob ("c:\\skitaid\\bin\\*"):
				os.remove (each)
			os.rmdir ("c:\\skitaid\\bin")	
		shutil.copytree ("skitai\\skitaid\\bin", "c:\\skitaid\\bin")
		if not os.path.isdir ("c:\\skitaid\\pub"):
			shutil.copytree ("skitai\\skitaid\\pub", "c:\\skitaid\\pub")
			
		print "\n\n======================================"
		print "Installation Complete"
		print "--------------------------------------"	
		print "Please run below command in your command prompt with administator privilege\n"
		print "  cd /d c:\\skitaid\\bin"
		print "  python install-win32-service.py --startup auto install"
		print "  python install-win32-service.py start"
	
	else:
			"""
			sudo rm -rf /etc/skitaid
			sudo rm -f /etc/init/skitaid.conf
			sudo rm -f /usr/local/bin/skitaid*
			sudo rm -rf /var/local/skitaid-pub
			"""
		
			if not os.path.isdir ("/etc/skitaid"):
				shutil.copytree ("skitai/skitaid/etc/skitaid", "/etc/skitaid")			
				os.remove ("/etc/skitaid/servers-enabled/default.conf")
				with open ("skitai/skitaid/etc/skitaid/servers-enabled/default.conf") as f:
					data = f.read ().replace ("c:\\skitaid\\pub\default\\", "/var/local/skitaid-pub/default/")
				with open ("/etc/skitaid/servers-enabled/default.conf", "w") as f:
					f.write (data)
				
			try: 
				os.mkdir ("/var/log/skitaid")
				os.mkdir ("/var/local/skitaid")				
			except OSError, why:
				if why [0] != 17:
					raise
	
			if os.path.isfile ("/etc/init/skitaid.conf"):
				os.remove ("/etc/init/skitaid.conf")
			shutil.copyfile ("skitai/skitaid/etc/init/skitaid.conf", "/etc/init/skitaid.conf")		
			if os.path.isfile ("/usr/local/bin/skitaid.py"):
				os.remove ("/usr/local/bin/skitaid.py")		
			if os.path.isfile ("/usr/local/bin/skitaid-instance.py"):
				os.remove ("/usr/local/bin/skitaid-instance.py")	
			shutil.copyfile ("skitai/skitaid/bin/skitaid.py", "/usr/local/bin/skitaid.py")
			shutil.copyfile ("skitai/skitaid/bin/skitaid-instance.py", "/usr/local/bin/skitaid-instance.py")
			
			if not os.path.isdir ("/var/local/skitaid-pub"):
				shutil.copytree ("skitai/skitaid/pub", "/var/local/skitaid-pub")
			
			os.chmod ("/usr/local/bin/skitaid.py", 0755)
			os.chmod ("/usr/local/bin/skitaid-instance.py", 0755)
		
			print "\n\n======================================"
			print "Installation Complete"
			print "--------------------------------------"	
			print "Please run below command in your command prompt\n"
			print "  sudo skitaid start"
			print "  wget http://www.localhost:5000"
	

	
