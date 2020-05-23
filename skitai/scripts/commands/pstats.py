import pstats
import os
from rs4.termcolor import tc
import getopt, sys

def main ():
    if not os.path.isfile ('profile.out'):
        print (tc.error ("error:"))
        print (" - profile.out file not found")
        print (" - for creating this file, run your app with ---profile")
        print ()
        return

    argopt = getopt.getopt (sys.argv[1:], "n:s:", ["sort="])
    SORT = 'ncalls'
    N = 300
    for k, v in argopt [0]:
        if k == '-s' or k == '--sort':
            SORT = v
        elif k == '-n':
            N = int (v)

    stats = pstats.Stats ('profile.out')
    stats.strip_dirs()
    stats.sort_stats(SORT)
    stats.print_stats(N)
    stats.print_callers ()

