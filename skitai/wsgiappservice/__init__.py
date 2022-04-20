from . import wasbase, deprecated
from .wastype import _WASType
from ..tasks import tasks

class WAS (wasbase.WASBase, deprecated.Deprecated):
    def __init__ (self, **options):
        self.options = options

    def _set_was_id (self, meta):
        meta = meta or {}
        meta ['__was_id'] = self.ID
        return meta

    def Tasks (self, *reqs, timeout = 10, meta = None, **kreqs):
        keys = []
        reqs_ = []
        if reqs and isinstance (reqs [0], (list, tuple)):
            reqs = reqs [0]

        for k, v in kreqs.items ():
            keys.append (k)
            reqs_.append (v)
        for v in reqs:
            keys.append (None)
            reqs_.append (v)
        return tasks.Tasks (reqs_, timeout, self._set_was_id (meta), keys)

    def Mask (self, data = None, _expt = None, _status_code = None, meta = None, keys = None):
        return tasks.Mask (data, _expt, _status_code, meta = self._set_was_id (meta), keys = keys)
