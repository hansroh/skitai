import pstats
import os
from rs4.termcolor import tc

def main ():
    if not os.path.isfile ('profile.out'):
        print (tc.error ("error:"))
        print (" - profile.out file not found")
        print (" - for creating this file, run your app with ---profile")
        print ()
        return
        
    p = pstats.Stats ('profile.out')
    p.strip_dirs().sort_stats("ncalls").print_stats(100)
    
