#! /usr/bin/env python3
# collect requirements of all skitai packages for pre install

import sys
import os
from rs4 import importer
import re

def collect ():
    requires_all= []
    devlibs = []
    libs = os.path.abspath (os.path.join (os.path.dirname (__file__), '../'))
    for lib in os.listdir (libs):
        path = os.path.join (libs, lib)
        if not os.path.isdir (path):
            continue
        os.chdir (path)
        try:
            tmp = importer.from_file ('tmp', os.path.join (libs, lib, 'setup.py'))
        except FileNotFoundError:
            continue

        devlibs.append (lib)
        try:
            requires = tmp.install_requires
            requires_all.extend (requires)
        except AttrubuteError:
            continue

    requires_wanted = set ()
    for lib in requires_all:
        name = re.split ('[=<>]', lib)[0]
        matched = False
        for _ in devlibs:
            if name == _:
                matched = True
                break
        if not matched:
            requires_wanted.add (lib)

    os.chdir (os.path.join (libs, 'skitai'))
    print ('found dependencies:')
    with open ('tools/docker/requirements.txt', 'w') as f:
        for r in requires_wanted:
            print ('-', r)
            f.write (r + '\n')


if __name__ == "__main__":
    collect ()
