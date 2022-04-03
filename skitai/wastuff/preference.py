import os
import sys
from rs4.attrdict import AttrDict
import copy

class PreferenceBase:
    def add_resources (self, module, front = False):
        base_dir = os.path.dirname (module.__file__)
        t = os.path.join (base_dir, 'templates')
        s = os.path.join (base_dir, 'static')
        os.path.isdir (t) and self.add_template_dir (t, front = front)
        os.path.isdir (s) and self.add_static (s, front = front)

    def extends (self, module):
        hasattr (module, '__config__') and module.__config__ (self)
        self.add_resources (module)
        self.mount_later ('/', module, extends = True)

    def overrides (self, module):
        if hasattr (module, '__file__'):
            hasattr (module, '__config__') and module.__config__ (self)
            self.add_resources (module, True)
        self.mount_later ('/', module, overrides = True)

    def add_template_dir (self, d, front = False):
        if "TEMPLATE_DIRS" not in self.config:
            self.config.TEMPLATE_DIRS = []
        exists = set (self.config.TEMPLATE_DIRS)
        if d in exists:
            return
        self.config.TEMPLATE_DIRS.insert (0, d) if front else self.config.TEMPLATE_DIRS.append (d)
        exists.add (d)

    def add_static (self, path, front = False):
        from skitai import mount, joinpath
        mount (self.config.STATIC_URL, joinpath (path), first = front)

    def set_static (self, url, path = None):
        from skitai import mount, joinpath
        self.config.STATIC_URL = url
        if path:
            path = joinpath (path)
            self.config.STATIC_ROOT = path
            mount (url, path, first = True)
    mount_static = set_static

    def set_media (self, url = '/media', path = None):
        from skitai import set_media
        self.config.MEDIA_URL = url
        self.config.MEDIA_ROOT = path
        set_media (url, path)
    mount_media = set_media

class Preference (AttrDict, PreferenceBase):
    def __init__ (self, path = None):
        from skitai import abspath

        super ().__init__ ()
        self.__path = path
        if self.__path:
            sys.path.insert (0, abspath (self.__path))
        self.__dict__ ["mountables"] = []

    def __enter__ (self):
        return self

    def __exit__ (self, *args):
        pass

    def copy (self):
        return copy.deepcopy (self)

    def mount_later (self, *args, **kargs):
        # mount module or func (app, options)
        self.__dict__ ["mountables"].append ((args, kargs))
