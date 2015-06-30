"""
Hans Roh 2015 -- http://sae.skitai.com
License: BSD
"""
import sys
import os
from warnings import warn

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
	"README.TXT", 
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

with open('requirements.txt') as f:
	required = f.read().splitlines()			

with open ("skitai/README.TXT") as f:
	ldesc = f.read ()

setup(
	name='skitai',
	version='0.9.1.3',
	description='Skitai App Engine Library',
	long_description = ldesc,
	author='Hans Roh',
	author_email='hansroh@gmail.com',
	url='https://gitlab.com/hansroh/skitai',
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	install_requires=required,
	license='BSD',
	zip_safe=False,
	classifiers=[
        'License :: OSI Approved :: BSD License',
        "Development Status :: 3 - Alpha",
        'Programming Language :: Python',        
        'Programming Language :: Python :: 2.7'        
    ],
)
