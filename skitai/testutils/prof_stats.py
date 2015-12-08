#!/usr/bin/python

import hotshot, hotshot.stats, test.pystone

#prof = hotshot.Profile("skitaid.prof")
#benchtime, stones = prof.runcall(test.pystone.pystones)
#prof.close()

stats = hotshot.stats.load("/home/ubuntu/skitai/skitaid-instance.prof")
stats.strip_dirs()
stats.sort_stats('time', 'calls')
stats.print_stats(20)
