import time, os
from rs4.psutil import processutil
from rs4.termcolor import tc

def due (sec):
    if sec < 60:
        return "{} seconds".format (int (sec))
    elif sec < 3600:
        return "{} minutes".format (sec // 60)
    elif sec < 86400:
        return "{:.1f} hours".format (sec / 3600)
    return "{:.1f} days".format (sec / 3600 / 24)

def main ():
    print ("existing apps:")
    default_var = os.path.expanduser ('~/.sktd')
    for each in sorted (os.listdir (default_var)):
        if each.startswith ('_'):
            continue
        if os.path.isdir (os.path.join (default_var, each)):
            plock = os.path.join (default_var, each, f".{each}.pid")
            running = False
            if os.path.isfile (plock):
                with open (plock) as f:
                    pid = int (f.read ())
                running = processutil.is_running (pid)

        if running:
            inst = tc.info (each)
            status = "running for {}, pid {}".format (due (time.time () - os.path.getmtime (plock)), tc.yellow (pid))
        else:
            inst = tc.primary (each)
            status = "stopped"
        print ("- {} {}".format (inst, status))
    print ("\nif you want to remove app from list,")
    print ("  rm -rf ~/.sktd/<app>")
