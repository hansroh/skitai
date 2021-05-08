import multiprocessing

class Semaps:
    def __init__ (self, keys, type = "d", slots = 256):
        self.slots = slots
        self._keys = []
        if type == "d":
            initial_val = 0.0
        else:
            initial_val = 0
        self._arr = multiprocessing.Array (type, [initial_val] * self.slots, lock = multiprocessing.RLock ())
        self._d = {}
        self._ints = set ()
        self.add (keys)

    def add (self, keys):
        initial = len (self._keys)
        for i, key in enumerate (keys):
            assert isinstance (key, str)
            if key in self._d:
                continue
            self._d [key] = initial + i
            self._keys.append (key)

    def __len__ (self):
        return len (self._d)

    def __contains__ (self, k):
        return k in self._d

    def __setitem__ (self, k, v):
        self.set (k, v)

    def __getitem__ (self, k):
        v = self.get (k, None)
        if v is None:
            raise KeyError ('key name `{}` is not exists'.format (k))
        return v

    def set (self, k, v, ignore_nokey = False):
        if k in self._ints:
            assert isinstacne (v, int), 'initial `{}` value type is int'.format (k)
        if isinstance (v, int):
            self._ints.add (k)
        try:
            self._arr [self._d [k]] = v
        except KeyError:
            if not ignore_nokey:
                raise

    def get (self, k, d = None):
        v = self._arr [self._d [k]]
        if not v and d:
            self._arr [self._d [k]] = d
            return d
        return int (v) if k in self._ints else v

    def delta (self, k, delta = 1):
        self.set (k, self.get (k) + delta)

    def has_key (self, k):
        return self._d.has_key (k)

    def keys (self):
        return self._keys [:]

    def values (self):
        t = []
        for i in range (len (self._keys)):
            t.append (self._arr [i])
        return t

    def items (self):
        t = []
        for i in range (len (self._keys)):
            t.append ((self._keys [i], self._arr [i]))
        return t


class TestSemaps (Semaps):
    def __init__ (self, keys = [], tpye= "d", slots = 256):
        self._keys = keys
        self._arr = [0] * slots
        self._ints = set ()
        self._d = {}

    def set (self, k, v, ignore_nokey = False):
        if k not in self._d:
            self._d [k] = len (self._d)
        self._arr [self._d [k]] = v
