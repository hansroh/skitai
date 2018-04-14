"""
2015. 12. 10
Hans Roh
"""
from . import part
from .Saddle import Saddle
import requests
from aquests.lib import siesta
from aquests.lib.pmaster import Puppet
import subprocess
import time
import sys
import os

# Events
app_starting = "app:starting"
app_started = "app:started"
app_restarting = "app:restarting"
app_restarted = "app:restarted"
app_mounted = "app:mounted"
app_unmounting = "app:umounting"

request_failed = "request:failed"
request_success = "request:success"
request_tearing_down = "request:teardown"
request_starting = "request:started"
request_finished = "request:finished"

template_rendering = "template:rendering"
template_rendered = "template:rendered"

# pytest framework ---------------------------------------------
        
class launch:
    def __init__ (self, script, endpoint = ":5000", silent = False):
        self.script = script
        if endpoint.startswith (":"):
            endpoint = "http://127.0.0.1" + endpoint
        while endpoint:
            if endpoint [-1] == "/":
                endpoint = endpoint [:-1]
            else:
                break
        self.endpoint = endpoint
        self.silent = silent
        self.p = Puppet (communicate = False)
        
        self.requests = Requests (endpoint)
        self.api = siesta.API (endpoint)
    
    def wait_until (self, status, timeout = 10):
        for i in range (timeout):
            command = "{} {} status".format (sys.executable, self.script)
            res = subprocess.run (command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)    
            out, err = res.stdout.decode ("utf8"), res.stderr.decode ("utf8")
            if out.find (status) != -1:
                break
            time.sleep (1) 
                
    def __enter__ (self):
        self.p.start ([sys.executable, self.script, self.silent and "-d" or "-v"])
        if self.silent:
            self.wait_until ("running")
        else:
            time.sleep (3)
        return self
        
    def __exit__ (self, type, value, tb):
        if self.silent:
            self.p.start ([sys.executable, self.script, "stop"])
            self.wait_until ("stopped")
        else:    
            self.p.kill ()
            time.sleep (3)


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
          