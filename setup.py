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
    os.system ('./collect_requires.py')
    os.system ('{} setup.py bdist_wheel'.format (sys.executable))
    whl = glob.glob ('dist/skitai-{}-*.whl'.format (version))[0]
    os.system ('twine upload {}'.format (whl))
    sys.exit ()

classifiers = [
    'License :: OSI Approved :: MIT License',
    'Development Status :: 4 - Beta',
    'Topic :: Internet :: WWW/HTTP :: WSGI',
    'Environment :: Console',
    'Environment :: No Input/Output (Daemon)',
    'Topic :: Internet',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Intended Audience :: Developers',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: Implementation :: CPython'
]

packages = [
    'skitai',
    'skitai.scripts',
    'skitai.scripts.commands',
    'skitai.backbone',
    'skitai.backbone.threaded',
    'skitai.handlers',
    'skitai.handlers.http2',
    'skitai.handlers.websocket',
    'skitai.tasks',
    'skitai.tasks.pth',
    'skitai.wsgiappservice',
    'skitai.wastuff',
    'skitai.mounted',
    'skitai.testutil',
    'skitai.testutil.offline',
]

package_dir = {'skitai': 'skitai'}
package_data = {
    "skitai": []
}

install_requires = [
    "rs4>=0.3.13",
    "sqlphile>=0.9",
    "h2>=4.0.0"
]
if os.name == "nt":
    install_requires.append ("pywin32")


if __name__ == "__main__":
    with codecs.open ('README.md', 'r', encoding='utf-8') as f:
        long_description = f.read()
    long_description = "[Documentation](https://gitlab.com/skitai/skitai/-/blob/master/README.md)"

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
