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
    print ('collecting dependencies:')
    for lib in os.listdir (libs):
        print ('-', lib)
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

    os.chdir (os.path.join (libs, 'skitai'))
    with open ('benchmark/requirements.txt') as f:
        for line in f:
            line = line.strip ()
            if not line:
                continue
            requires_all.append (line)

    with open ('tests/requirements.txt') as f:
        for line in f:
            line = line.strip ()
            if not line:
                continue
            requires_all.append (line)

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

    print ('found dependencies:')
    with open ('tools/docker/requirements.txt', 'w') as f:
        for r in requires_wanted:
            print ('-', r)
            f.write (r + '\n')


if __name__ == "__main__":
    collect ()
