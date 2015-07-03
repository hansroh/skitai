"""
Hans Roh 2015 -- http://sae.skitai.com
License: BSD
"""
__VER__ = '0.9.1.16'

import sys
import os
from warnings import warn
import setuptools

try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

if sys.argv[-1] == 'publish':
	os.system('python setup.py sdist bdist_wininst --target-version=2.7 upload') # bdist_wininst
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
	"implements/skitaid/app/*.*",
	"implements/skitaid/app/static/*.*",
	"implements/skitaid/bin/*.*", 
	"implements/skitaid/bin/win32service/*.*",
	"implements/skitaid/etc/init/skitaid.conf", 
	"implements/skitaid/etc/init.d/skitaid", 
	"implements/skitaid/etc/skitaid/skitaid.conf", 
	"implements/skitaid/etc/skitaid/servers-available/README.TXT", 
	"implements/skitaid/etc/skitaid/servers-enabled/sample.conf",
	"implements/skitaid/etc/skitaid/cert/generate/*.*"
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
	description='Skitai App Engine Library',
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
