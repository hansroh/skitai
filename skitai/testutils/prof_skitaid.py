#!/usr/bin/python

import hotshot, hotshot.stats, test.pystone

prof = hotshot.Profile("stones.prof")
prof.run ("skitaid-instance.py -v -f test")

