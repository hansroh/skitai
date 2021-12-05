import sys
import os
from .commands import smtpda, status, pstats

def help ():
    print ("usage: skitai <command> [<options>]")
    print ("command:")
    print ("  smtpda")
    print ("  status")
    print ("  pstats")
    sys.exit ()

def main ():
    try:
        cmd = sys.argv [1]
    except IndexError:
        help ()

    sys.argv.pop (1)
    if cmd == "smtpda":
        smtpda.main ()
    elif cmd == "status":
        status.main ()
    elif cmd == "pstats":
        pstats.main ()
    else:
        print ("unknown conmand")


if __name__ == "__main__":
    main ()
