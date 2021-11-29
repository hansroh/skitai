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

if 'publish' in sys.argv:
    import collect_requires; collect_requires.collect ()
    os.system ('{} setup.py bdist_wheel'.format (sys.executable))
    whl = glob.glob ('dist/skitai-{}-*.whl'.format (version))[0]
    os.system ('twine upload {}'.format (whl))
    sys.exit ()

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
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: Implementation :: CPython'
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
    'skitai.tasks',
    'skitai.tasks.dbi',
    'skitai.tasks.httpbase',
    'skitai.tasks.pth',
    'skitai.wsgiappservice',
    'skitai.wastuff',
    'skitai.mounted',
    'skitai.testutil',
    'skitai.testutil.offline',
    'skitai.protocols',
    'skitai.protocols.threaded',
    'skitai.protocols.dbi',
    'skitai.protocols.dbi.impl',
    'skitai.protocols.sock',
    'skitai.protocols.sock.impl',
	'skitai.protocols.sock.impl.dns',
	'skitai.protocols.sock.impl.dns.pydns',
	'skitai.protocols.sock.impl.http',
	'skitai.protocols.sock.impl.http2',
	'skitai.protocols.sock.impl.http2.hyper',
	'skitai.protocols.sock.impl.http2.hyper.common',
	'skitai.protocols.sock.impl.http2.hyper.http11',
	'skitai.protocols.sock.impl.http2.hyper.http20',
	'skitai.protocols.sock.impl.http2.hyper.http20.h2',
	'skitai.protocols.sock.impl.http2.hyper.packages',
	'skitai.protocols.sock.impl.http2.hyper.packages.rfc3986',
    'skitai.protocols.sock.impl.http3',
	'skitai.protocols.sock.impl.ws',
	'skitai.protocols.sock.impl.smtp',
	'skitai.protocols.sock.impl.grpc',
	'skitai.protocols.sock.impl.proxy',
]

package_dir = {'skitai': 'skitai'}
package_data = {
    "skitai": [
        "protocols/sock/impl/dns/*.txt",
		"protocols/sock/impl/dns/pydns/*.txt",
		"protocols/sock/impl/http2/hyper/*.txt",
		"protocols/sock/impl/http2/hyper/*.pem",
        "protocols/sock/impl/http3/*.pem",
    ]
}

install_requires = [
    "rs4>=0.3",
    "sqlphile>=0.9",
    "h2>=4.0.0"
]
if os.name == "nt":
    install_requires.append ("pywin32")

with codecs.open ('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()


if __name__ == "__main__":
    setup (
        name='skitai',
        version=version,
        description='Skitai App Engine',
        long_description=long_description,
        long_description_content_type = 'text/markdown',
        url = 'https://gitlab.com/skitai/skitai',
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
