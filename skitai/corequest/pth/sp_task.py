# Subprocess Task

from . import task
import subprocess
from concurrent.futures import TimeoutError
from ..tasks import Mask
import time
from skitai import was

class Task (task.Task):
    def __init__ (self, cmd, timeout):
        self._timeout = timeout
        self._name = cmd
        self._started = time.time ()
        self._was = None
        self._fulfilled = None
        self._mask = None
        self.proc = subprocess.Popen (cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell = True)

    @property
    def lines (self):
        for line in iter (self.proc.stdout.readline, b''):
            yield line

    def _polling (self):
        mask = self._create_mask (self._timeout)
        self._late_respond (mask)

    def then (self, func):
        self._fulfilled = func
        self._was = self._get_was ()
        was.Thread (self._polling)

    def kill (self):
        self.proc.kill ()

    def terminate (self):
        self.proc.terminate ()

    def _create_mask (self, timeout):
        self._timeout = timeout
        if self._mask:
            return self._mask

        data, expt = None, None
        try:
            data, err = self.proc.communicate (timeout = timeout)
        except subprocess.TimeoutExpired:
            expt = TimeoutError
            self.proc.terminate ()
            self.proc.wait ()
        else:
            if self.proc.returncode:
                if isinstance (err, bytes):
                    err = err.decode ()
                expt = SystemError ('code:{} {}'.format (self.proc.returncode, err))
        self._mask = Mask (data, expt)
        return self._mask


