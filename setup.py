"""
Hans Roh 2015 -- http://osp.skitai.com
License: BSD
"""
import re
import sys
import os
import shutil, glob
import codecs
from warnings import warn
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

if sys.argv[-1] == 'publish':
	if os.name == "nt":
		os.system('python setup.py sdist upload') # bdist_wininst --target-version=2.7
	else:
		os.system('python setup.py sdist; twine upload dist/*; rm dist/*')
	sys.exit()

classifiers = [
  'License :: OSI Approved :: MIT License',
  'Development Status :: 4 - Beta',
  'Topic :: Internet :: WWW/HTTP :: HTTP Servers',	
	'Topic :: Internet :: WWW/HTTP :: WSGI',
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
	'skitai.server.bin',
	'skitai.server.wastuff',
	'skitai.server.handlers',
	'skitai.server.rpc',	
	'skitai.server.handlers.http2',
	'skitai.server.handlers.websocket',
	'skitai.server.handlers.proxy',
	'skitai.saddle',
	'skitai.saddle.patches'
]

package_dir = {'skitai': 'skitai'}
package_data = {}

install_requires = [
	"jinja2==2.9.4", 
	"chameleon==3.1", 	
	"aquests>=0.7.3.2"
]

with open('skitai/__init__.py', 'r') as fd:
	version = re.search(r'^__version__\s*=\s*"(.*?)"',fd.read(), re.M).group(1)

with codecs.open ('README.rst', 'r', encoding='utf-8') as f:
	long_description = f.read()
    
setup(
	name='skitai',
	version=version,
	description='Skitai App Engine For Microservices',
	long_description=long_description,
	url = 'https://gitlab.com/hansroh/skitai',
	author='Hans Roh',
	author_email='hansroh@gmail.com',	
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	license='MIT',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/skitai",
	install_requires = install_requires,
	classifiers=classifiers
)
