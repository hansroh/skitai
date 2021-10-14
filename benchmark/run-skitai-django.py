#!/usr/bin/env python3

from atila import Atila
from sqlphile import Q

app = Atila (__name__)

if __name__ == '__main__':
    import skitai, os
    with skitai.preference (path = os.path.abspath (os.path.join (os.path.dirname (__file__), 'bench'))) as pref:
        skitai.mount ("/", 'bench/bench/wsgi:application', pref)
    skitai.run (workers = 4, threads = 4, port = 5000)
