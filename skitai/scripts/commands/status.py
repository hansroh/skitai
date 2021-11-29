import time, os
from rs4.psutil import processutil
from rs4.termcolor import tc
import sys

default_var = os.path.expanduser ('~/.skitai')

def due (sec):
    if sec < 60:
        return "{} seconds".format (int (sec))
    elif sec < 3600:
        return "{} minutes".format (sec // 60)
    elif sec < 86400:
        return "{:.1f} hours".format (sec / 3600)
    return "{:.1f} days".format (sec / 3600 / 24)

def status (name, detail):
    if not os.path.exists (os.path.join (default_var, name)):
        return

    running = False
    plock = os.path.join (default_var, name, f".{name}.pid")
    if os.path.isfile (plock):
        with open (plock) as f:
            pid = int (f.read ())
        running = processutil.is_running (pid)

    if running:
        inst = tc.info (name)
        status = "running for {}, pid {}".format (due (time.time () - os.path.getmtime (plock)), tc.yellow (pid))
    else:
        inst = tc.primary (name)
        status = "stopped"

    print ("{} {}".format (inst, status))
    log_path = os.path.join (default_var, name, 'log')
    if os.path.isdir (log_path):
        for log in os.listdir (log_path):
            print (f'- {tc.yellow (log)}')
            if not detail:
                continue
            p = max (0, os.path.getsize (os.path.join (log_path, log)) - 65535)
            with open (os.path.join (log_path, log)) as f:
                f.seek (p)
                d = f.read ()
            for line in d.split ('\n')[-3:-1]:
                if not line:
                    continue
                print (f'  + {line}')

def main ():
    detail = False
    if len (sys.argv) == 2:
        names = [sys.argv [1]]
        detail = True
    else:
        names = sorted (os.listdir (default_var))

    for name in names:
        if name.startswith ('.'):
            continue
        status (name, detail)

    print ("\nif you want to remove app from list,")
    print ("  rm -rf ~/.skitai/<app>")
