"""
Hans Roh 2015 -- http://sae.skitai.com
"""
import sys
import os

try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

if sys.argv[-1] == 'publish':
	os.system('python setup.py sdist bdist_wininst upload') # bdist_wininst
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

if os.name == "posix":
	with open('requirements.txt') as f:
		required = f.read().splitlines()
else:
	# win32, install manually
	required = []


setup(
	name='skitai',
	version='0.9.0',
	description='Skitai App Engine Library',
	author='Hans Roh',
	author_email='hansroh@gmail.com',
	url='https://gitlab.com/hansroh/skitai',
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	install_requires=required,
	license='BSD',
	zip_safe=False,
)
