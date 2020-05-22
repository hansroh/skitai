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
	'Programming Language :: Python :: 3.5',
	'Programming Language :: Python :: 3.6',
	'Programming Language :: Python :: 3.7',
	'Programming Language :: Python :: Implementation :: CPython',
	'Programming Language :: Python :: Implementation :: PyPy'
]

packages = [
	'skitai',
	'skitai.scripts',
	'skitai.scripts.commands',
	'skitai.backbone',
	'skitai.handlers',
	'skitai.handlers.http2',
	'skitai.handlers.websocket',
	'skitai.handlers.proxy',
	'skitai.corequest',
	'skitai.corequest.dbi',
	'skitai.corequest.httpbase',
	'skitai.corequest.pth',
	'skitai.wastuff',
	'skitai.mounted',
	'skitai.testutil'
]

package_dir = {'skitai': 'skitai'}
package_data = {}

install_requires = [
	"rs4>=0.2.5.0",
	"aquests>=0.29.2.0",
	"jsonrpclib-pelix",
	"sqlphile",
]
if os.name == "nt":
	install_requires.append ("pywin32")
else:
	install_requires.append ("ujson-ia")

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
			'skitai=skitai.scripts.skitai:main',
		],
    },
	license='MIT',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/skitai",
	install_requires = install_requires,
	classifiers=classifiers
)
