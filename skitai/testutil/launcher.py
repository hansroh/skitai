# pytest framework ---------------------------------------------
import requests
from rs4 import siesta, webtest
from rs4.psutil import Puppet, processutil
import subprocess
import time
import sys
import os
import xmlrpc.client 
    
class Launcher (webtest.Target):
    def __init__ (self, script, port, ssl = False, silent = True, dry = False, **kargs):
        self.__script = script
        self.__port = port
        
        self.__start_opts = ["--port", str (port)]
        for k, v in kargs:
            self.__start_opts.append ("--{}".format (k))
            if v:
                self.__start_opts.append (str (v))
            
        endpoint = "http{}://127.0.0.1".format (ssl and "s" or "")
        endpoint += ":{}".format (port)
        webtest.Target.__init__ (self, endpoint)
        self.__silent = silent
        self.__dry = dry
        self.__servicing = False
        self.__p = Puppet (communicate = False)        
        self.__closed = True
        self.__start ()
            
    def __start (self):
        if self.__dry:
            return
        
        if self.__silent:
            if self.__is_running ():
                self.__servicing = True
            else:    
                self.__p.start ([sys.executable, self.__script, "-d"] + self.__start_opts)
                self.__wait_until ("running")
        else:
            self.__p.start ([sys.executable, self.__script]  + self.__start_opts)
            time.sleep (3)
        self.__closed = False
        
    def __is_running (self):
        command = "{} {} status".format (sys.executable, self.__script)
        res = subprocess.run (command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)    
        out, err = res.stdout.decode ("utf8"), res.stderr.decode ("utf8")
        return out.find ("running") != -1

    def __wait_until (self, status, timeout = 10):
        for i in range (timeout):
            command = "{} {} status".format (sys.executable, self.__script)
            res = subprocess.run (command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)    
            out, err = res.stdout.decode ("utf8"), res.stderr.decode ("utf8")
            if out.find (status) != -1:
                return
            time.sleep (1)
    
    def _close (self):
        if self.__closed:
            return        
        if self.__silent and not self.__servicing:
            self.__p.start ([sys.executable, self.__script, "stop"])
            self.__wait_until ("stopped")
        else:
            self.__p.kill ()
            time.sleep (3)
        self.__closed = True
    stop = _close
        
launch = Launcher
    