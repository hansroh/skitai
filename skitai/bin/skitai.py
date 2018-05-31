import sys
from . import smtpda
 
def help ():
    print ("usage: skitai <command> [<options>]")
    print ("command:")
    print ("  smtpda")
    print ("  cron")
    sys.exit ()
     
def main ():    
    try: 
        cmd = sys.argv [1]
    except IndexError:
        help ()
    sys.argv.pop (1)    
    if cmd == "smtpda":
        smtpda.main ()


if __name__ == "__main__":
    main ()
