# Subprocess Task

from . import task
import subprocess
from concurrent.futures import TimeoutError
from ..tasks import Mask
import time
from skitai import was

class Task (task.Task):
    def __init__ (self, was_id, cmd, timeout):
        self.setup (was_id, cmd, timeout)
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
        self._mask = Mask (data, expt, meta = self.meta)
        return self._mask


