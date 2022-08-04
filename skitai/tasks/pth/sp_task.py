# Subprocess Task

from . import task
import subprocess
from concurrent.futures import TimeoutError
from ..derivations import Mask
import skitai

class Task (task.Task):
    def __init__ (self, cmd, meta, filter = None, timeout = None):
        self.setup (cmd, meta, filter, timeout)
        self.proc = subprocess.Popen (cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell = True)

    def __getattr__ (self, name):
        raise AttributeError

    @property
    def lines (self):
        for line in iter (self.proc.stdout.readline, b''):
            yield line

    def then (self, func, was = None):
        self._fulfilled = func
        self._was = was or self._get_was ()
        return skitai.was.Thread (self._settle)

    def _settle (self, future = None):
        if self._fulfilled:
            mask = self._create_mask (0)
            if '__reqid' in self._meta:
                self._fulfilled (mask)
                self._fulfilled = None
            else:
                self._late_respond (mask)

    def set_callback (self, func, reqid = None, timeout = None):
        if reqid is not None:
            self._meta ["__reqid"] = reqid
        self._timeout = timeout
        self._fulfilled = func
        skitai.was.Thread (self._settle)

    def kill (self):
        self.proc.kill ()

    def terminate (self):
        self.proc.terminate ()

    def _create_mask (self, timeout):
        if timeout:
            self._timeout = timeout
        if self._mask:
            return self._mask

        data, expt = None, None
        try:
            data, err = self.proc.communicate (timeout = self._timeout)
        except subprocess.TimeoutExpired:
            expt = TimeoutError
            self.proc.terminate ()
            self.proc.wait ()
        else:
            if self.proc.returncode:
                if isinstance (err, bytes):
                    err = err.decode ()
                expt = SystemError ('code:{} {}'.format (self.proc.returncode, err))
        if isinstance (data, bytes):
            data = data.decode ()
        if self._filter:
            data =  self._filter (data)
        self._mask = Mask (data, expt, meta = self.meta)
        return self._mask
