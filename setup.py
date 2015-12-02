"""
Hans Roh 2015 -- http://osp.skitai.com
License: BSD
"""

__VER__ = '0.9.4.11'

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
  "Development Status :: 3 - Alpha",
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
    
packages = [
	'skitai',
	'skitai.client',
	'skitai.dbapi',
	'skitai.lib',	
	'skitai.protocol',
	'skitai.protocol.dns',
	'skitai.protocol.dns.pydns',
	'skitai.protocol.http',	
	'skitai.protocol.smtp',
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
	"skitaid/etc/skitaid/servers-available/README.txt", 
	"skitaid/etc/skitaid/servers-enabled/default.conf",
	"skitaid/etc/skitaid/cert/*.*",
	"protocol/dns/*.txt",
	"protocol/dns/pydns/*.txt"
]

package_data = {
	"skitai": skitaid_files
}

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
	license='BSD',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/skitai",
	classifiers=classifiers
)

if "install" in sys.argv or "develop" in sys.argv:
	if os.name == "nt":
		if not os.path.isdir ("c:\\skitaid"):
			os.mkdir ("c:\\skitaid")
			os.mkdir ("c:\\skitaid\\var")
			os.mkdir ("c:\\skitaid\\log")
			shutil.copytree ("skitai\\skitaid\\etc\\skitaid", "c:\\skitaid\\etc")
		
		if os.path.isdir ("c:\\skitaid\\bin"):
			for fn in os.listdir ("skitai\\skitaid\\bin"):
				try: os.remove (os.path.join ("c:\\skitaid\\bin", fn))
				except WindowsError as why:
					if why.errno == 2: pass	
				shutil.copyfile (os.path.join ("skitai\\skitaid\\bin", fn), os.path.join ("c:\\skitaid\\bin", fn))
		
		if not os.path.isdir ("c:\\skitaid\\pub"):
			shutil.copytree ("skitai\\skitaid\\pub", "c:\\skitaid\\pub")
			
		print("\n\n======================================")
		print("Installation Complete")
		print("--------------------------------------")	
		print("Please run below command in your commands prompt with administator privilege\n")
		print("  cd /d c:\\skitaid\\bin")
		print("  python install-win32-service.py --startup auto install")
		print("  python install-win32-service.py start")
		print("  then check http://localhost:5000\n\n")
	
	else:
			"""
			sudo rm -rf /etc/skitaid
			sudo rm -f /etc/init/skitaid.conf
			sudo rm -f /etc/init.d/skitaid
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
			except OSError as why:
				if why.errno != 17:
					raise
			
			if os.path.isfile ("/etc/init/skitaid.conf"):
				os.remove ("/etc/init/skitaid.conf")
			if os.path.isfile ("/etc/init.d/skitaid"):
				os.remove ("/etc/init.d/skitaid")				
			shutil.copyfile ("skitai/skitaid/etc/init.d/skitaid", "/etc/init.d/skitaid")
			os.chmod ("/etc/init.d/skitaid", 0o755)
			
			if os.path.isfile ("/usr/local/bin/skitaid.py"):
				os.remove ("/usr/local/bin/skitaid.py")
			if os.path.isfile ("/usr/local/bin/skitaid-instance.py"):
				os.remove ("/usr/local/bin/skitaid-instance.py")	
			if os.path.isfile ("/usr/local/bin/skitaid-smtpda.py"):
				os.remove ("/usr/local/bin/skitaid-smtpda.py")	
			
			shutil.copyfile ("skitai/skitaid/bin/skitaid.py", "/usr/local/bin/skitaid.py")
			shutil.copyfile ("skitai/skitaid/bin/skitaid-instance.py", "/usr/local/bin/skitaid-instance.py")
			shutil.copyfile ("skitai/skitaid/bin/skitaid-smtpda.py", "/usr/local/bin/skitaid-smtpda.py")
			
			if not os.path.isdir ("/var/local/skitaid-pub"):
				shutil.copytree ("skitai/skitaid/pub", "/var/local/skitaid-pub")
			
			os.chmod ("/etc/skitaid/skitaid.conf", 0o600)
			os.chmod ("/usr/local/bin/skitaid.py", 0o755)
			os.chmod ("/usr/local/bin/skitaid-instance.py", 0o755)
			os.chmod ("/usr/local/bin/skitaid-smtpda.py", 0o755)
			
			print("\n\n======================================")
			print("Installation Complete")
			print("--------------------------------------")	
			print("Please run below commands\n")
			print("  sudo service skitaid start")
			print("  wget http://localhost:5000\n\n")
	

	
