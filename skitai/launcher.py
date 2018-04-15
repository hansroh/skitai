# pytest framework ---------------------------------------------
import requests
from aquests.lib import siesta
from aquests.lib.pmaster import Puppet, processutil
import subprocess
import time
import sys
import os

class launch:
    def __init__ (self, script, port = 5000, ssl = False, silent = True):
        self.__script = script
        endpoint = "http{}://127.0.0.1".format (ssl and "s" or "")
        if port:
            endpoint += ":{}".format (port)
        self.__endpoint = endpoint
        self.__silent = silent
        self.__servicing = False
        self.__p = Puppet (communicate = False)        
        self.__requests = Requests (endpoint)
        self.__api = siesta.API (endpoint)
        self.__closed = True
        self.__start ()
    
    def __enter__ (self):
        return self
        
    def __exit__ (self, type, value, tb):
        self._close ()
    
    def __del__ (self):
        self._close ()
         
    def __getattr__ (self, attr):
        if attr in ("get", "post", "put", "patch", "delete", "head", "options"):
            return getattr (self.__requests, attr)
        else:
            return getattr (self.__api, attr)
        
    def __start (self):
        if self.__silent:
            if self.__is_running ():
                self.__servicing = True
            else:    
                self.__p.start ([sys.executable, self.__script, "-d"])
                self.__wait_until ("running")
        else:
            self.__p.start ([sys.executable, self.__script, "-v"])
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

class Requests:
    def __init__ (self, endpoint):
        self.endpoint = endpoint
        self.s = requests.Session ()
    
    def resolve (self, url):
        if url.startswith ("http://") or url.startswith ("https://"):
            return url
        else:
            return self.endpoint + url 
        
    def get (self, url, *args, **karg):
        return self.s.get (self.resolve (url), *args, **karg)
        
    def post (self, url, *args, **karg):
        return self.s.post (self.resolve (url), *args, **karg)
    
    def put (self, url, *args, **karg):
        return self.s.put (self.resolve (url), *args, **karg)
    
    def patch (self, url, *args, **karg):
        return self.s.patch (self.resolve (url), *args, **karg)
    
    def delete (self, url, *args, **karg):
        return self.s.delete (self.resolve (url), *args, **karg)
    
    def head (self, url, *args, **karg):
        return self.s.head (self.resolve (url), *args, **karg)
                
    def options (self, url, *args, **karg):
        return self.s.options (self.resolve (url), *args, **karg)
          