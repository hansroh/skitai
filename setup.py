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
	'Programming Language :: Python :: 3'
]

packages = [
	'skitai',
	'skitai.server',
	'skitai.server.dbi',
	'skitai.server.handlers',
	'skitai.server.rpc',
	'skitai.server.threads',
	'skitai.server.handlers.http2',
	'skitai.server.handlers.websocket',
	'skitai.server.handlers.proxy',
	'skitai.saddle',
	'skitai.examples'
]

package_dir = {'skitai': 'skitai'}

package_data = {
	"skitai": ["examples/grpc/*.proto"]
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
	install_requires = ["jinja2==2.8", "h2", "aquests"],
	classifiers=classifiers
)
