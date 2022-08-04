# pytest framework ---------------------------------------------
from rs4.webkit import webtest
from rs4.psutil import Puppet
import subprocess
import time
import sys

class Launcher (webtest.Target):
    def __init__ (self, script = None, port = 5000, devel = False, ssl = False, silent = True, dry = False, temp_dir = None, **kargs):
        if not script and not dry:
            raise TypeError ('script is not given while not dry-run')
        if not script:
            dry = True
            self.__script, self.__start_opts = None, []
        else:
            argv = script.split ()
            self.__script = argv [0]
            self.__start_opts = argv[1:]
            self.__start_opts.extend (["--port", str (port)])
            if devel:
                self.__start_opts.append ('--devel')
            for k, v in kargs.items ():
                self.__start_opts.append ("--{}".format (k))
                if v and isinstance (v, (str, int, float)):
                    self.__start_opts.append (str (v))

        endpoint = "http{}://127.0.0.1".format (ssl and "s" or "")
        endpoint += ":{}".format (port)
        webtest.Target.__init__ (self, endpoint, temp_dir = temp_dir)

        self.__dry = dry
        self.__port = port
        self.__silent = silent
        self.__servicing = False
        self.__p = Puppet (communicate = False)
        self.__closed = True
        self.__start ()

    def ensure_directory (self, url):
        if not url:
            url = "/"
        elif url [-1] != "/":
            url += "/"
        return url

    def rpc (self, url, proxy_class = None):
        return super ().rpc (self.ensure_directory (url), proxy_class)

    def jsonrpc (self, url, proxy_class = None):
        return super ().jsonrpc (self.ensure_directory (url), proxy_class)

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
            time.sleep (8)
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
        if self.__dry:
            self.__closed = True
            return
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
