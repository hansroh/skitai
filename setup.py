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

with open('skitai/__init__.py', 'r') as fd:
	version = re.search(r'^__version__\s*=\s*"(.*?)"',fd.read(), re.M).group(1)

if 'develop' in sys.argv[1:]:
	# For reseting entry point
	os.system ("rm -rf /usr/local/lib/python3.5/dist-packages/aquests-*")
	
if sys.argv[-1] == 'publish':
	buildopt = ['sdist', 'upload']	
	if os.name == "nt":
		buildopt.insert (0, 'bdist_wheel')
	os.system('python setup.py %s' % " ".join (buildopt))
	for each in os.listdir ("dist"):
		os.remove (os.path.join ('dist', each))
	sys.exit()
	
classifiers = [
  'License :: OSI Approved :: MIT License',
  'Development Status :: 4 - Beta',
  'Topic :: Internet :: WWW/HTTP :: HTTP Servers',	
	'Topic :: Internet :: WWW/HTTP :: WSGI',
	'Environment :: Console',
	'Environment :: No Input/Output (Daemon)',
	'Topic :: Internet',
	'Topic :: Software Development :: Libraries :: Python Modules',
	'Intended Audience :: Developers',	
	'Programming Language :: Python :: 3',
]

packages = [
	'skitai',
	'skitai.bin',
	'skitai.bin.commands',	
	'skitai.dbi',
	'skitai.wastuff',
	'skitai.handlers',
	'skitai.rpc',
	'skitai.mounted',		
	'skitai.testutil',
	'skitai.handlers.http2',
	'skitai.handlers.websocket',
	'skitai.handlers.proxy'
]

package_dir = {'skitai': 'skitai'}
package_data = {}

install_requires = [	
	"aquests",	
	"jsonrpclib-pelix",
	"sqlphile"
]

with codecs.open ('README.rst', 'r', encoding='utf-8') as f:
	long_description = f.read()
    
setup (
	name='skitai',
	version=version,
	description='Skitai App Engine',
	long_description=long_description,
	url = 'https://gitlab.com/hansroh/skitai',
	author='Hans Roh',
	author_email='hansroh@gmail.com',	
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	entry_points = {
        'console_scripts': [
			'skitai=skitai.bin.skitai:main',
		],
    },
	license='MIT',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/skitai",
	install_requires = install_requires,
	classifiers=classifiers	
)
