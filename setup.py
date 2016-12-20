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
	'skitai.examples',
	'skitai.protocol.dns',
	'skitai.protocol.dns.pydns',
	'skitai.protocol.http',	
	'skitai.protocol.ws',	
	'skitai.protocol.smtp',
	'skitai.server',
	'skitai.server.dbi',
	'skitai.server.handlers',
	'skitai.server.rpc',
	'skitai.server.threads',
	'skitai.server.handlers.http2',
	'skitai.server.handlers.websocket',
	'skitai.server.handlers.proxy',
	'skitai.saddle'
]

package_dir = {
	'skitai': 'skitai',
	'skitai.server': 'skitai/server'
}

skitai_files = [
	"protocol/dns/*.txt",
	"protocol/dns/pydns/*.txt"
]

package_data = {
	"skitai": skitai_files
}

setup(
	name='skitai',
	version=__VER__,
	description='Skitai Library',
	url = 'https://gitlab.com/hansroh/skitai',
	author='Hans Roh',
	author_email='hansroh@gmail.com',	
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	license='BSD',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/skitai",
	install_requires = ["jinja2==2.8", "h2"],
	classifiers=classifiers
)
