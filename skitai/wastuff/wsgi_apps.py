import inspect
import asyncio
import os, sys, re, types, time
from rs4  import pathtool, importer, evbus
from rs4.termcolor import tc
import threading
from types import FunctionType as function
import copy
from .. import lifetime
import inspect
from rs4 import attrdict, importer
from importlib import reload
from urllib.parse import unquote
import skitai
import time

def set_default (cf):
    cf.MAX_UPLOAD_SIZE = 256 * 1024 * 1024

def Config (preset = False):
    cf = attrdict.AttrDict ()
    if preset:
        set_default (cf)
    return cf


class DjangoReloader:
    def __init__ (self, mounted, logger):
        from django.utils import autoreload

        self.mounted = mounted
        self.logger = logger
        self.mtimes = {}
        self.version = 1
        if hasattr (autoreload, "code_changed"):
            self.reloader = autoreload
        else:
            self.version = 2
            self.reloader = autoreload.get_reloader ()

    def reloaded (self):
        if self.version == 1:
            return self.reloader.code_changed ()
        else:
            for filepath, mtime in self.reloader.snapshot_files ():
                if not str (filepath).startswith (self.mounted):
                    continue
                old_time = self.mtimes.get (filepath)
                self.mtimes [filepath] = mtime
                if old_time is None:
                    continue
                elif mtime > old_time:
                    return True
        return False


class Module:
    def __init__ (self, wasc, handler, bus, route, directory, libpath, pref = None):
        self.wasc = wasc
        self.bus = bus
        self.handler = handler
        self.pref = pref
        self.last_reloaded = time.time ()
        self.set_route (route)
        self.directory = directory
        self.has_life_cycle = False

        self.app = None
        self.app_initer = None
        self.django = False
        self.debug = False
        self.use_reloader = False

        if type (libpath) is str:
            try:
                libpath, self.appname = libpath.split (":", 1)
            except ValueError:
                libpath, self.appname = libpath, "app"
            self.libpath = libpath
            self.script_name = "%s.py" % libpath

            if 'services' in sys.modules:
                sys.modules.pop ('services')
            self.module, self.abspath = importer.importer (directory, libpath)
            self.start_app ()
            sys.path.insert (0, directory)

        else:
            # libpath is app object, might be added by unittest
            self.appname = 'app'
            if hasattr (libpath, '__app__'):
                self.app_initer = libpath
                self.module = libpath
                self.abspath = os.path.abspath (libpath.__file__)
                self.directory = os.path.dirname (self.abspath)
                self.app = libpath.__app__ ()

            else:
                self.module = None
                self.abspath = os.path.join (directory, '__nonextist__')
                self.directory = directory
                self.app = libpath
                self.app.use_reloader = False
                if hasattr (self.app, "path") and self.app.path:
                    self.app_initer = importer.from_file ("__temp", os.path.normpath (os.path.abspath (self.app.path)))

            self.start_app ()

    def __repr__ (self):
        return "<Module routing to %s at %x>" % (self.route, id(self))

    def get_callable (self):
        return self.app or getattr (self.module, self.appname)

    def start_app (self, reloded = False):
        func = None
        app = self.app or getattr (self.module, self.appname)
        self.has_life_cycle = hasattr (app, "life_cycle")
        if hasattr (app, "set_logger"):
            app.set_logger (self.wasc.logger.get ("app"))

        if str (app.__class__).find ("django.") != -1:
            django_base_dir = os.path.dirname (self.abspath)
            self.django = DjangoReloader (django_base_dir, self.wasc.logger)

        if self.pref:
            for k, v in copy.copy (self.pref).items ():
                if k == "config":
                    if not hasattr (app, 'config'):
                        app.config = v
                    else:
                        for k1, v1 in copy.copy (self.pref.config).items ():
                            app.config [k1] = v1
                elif k in ('mountables',):
                    if hasattr (app, k):
                        app.mountables.extend (v)
                    else:
                        setattr (app, k, v)
                else:
                    setattr (app, k, v)
        self.set_devel_env (app) # enforcing to override --devel

        if hasattr (app, "_aliases"):
            while app._aliases:
                self.wasc.add_cluster (*app._aliases.pop (0))

        if not hasattr (app, "config"):
            app.config = Config (False)

        if hasattr (app, "max_client_body_size"):
            app.config.MAX_UPLOAD_SIZE = app.max_client_body_size
        elif "max_multipart_body_size" in app.config:
            app.config.MAX_UPLOAD_SIZE = app.config.max_multipart_body_size

        mntopt = {
            'point': self.route,
            'base_dir': self.directory,
            'use_reloader': self.use_reloader,
            'debug': self.debug,
            'wasc': self.wasc
        }

        hasattr (app, "set_wasc") and app.set_wasc (self.wasc)
        hasattr (self.app_initer, '__setup__') and self.wasc.execute_function (self.app_initer.__setup__, (app, mntopt))
        hasattr (self.app_initer, '__mount__') and self.wasc.execute_function (self.app_initer.__mount__, (app, mntopt))
        hasattr (app, "set_home") and app.set_home (os.path.dirname (self.abspath), self.module)
        hasattr (app, "commit_events_to") and app.commit_events_to (self.bus)

        self.update_file_info ()

        try:
            if not reloded:
                func = app.start
            else:
                func = app.restart
        except AttributeError:
            pass

        if func:
            # temporary current handler
            self.wasc.handler = self.handler
            func (self.wasc, self.route)
            self.wasc.handler = None

        hasattr (self.app_initer, '__mounted__') and self.wasc.execute_function (self.app_initer.__mounted__, (app, mntopt))

    def before_mount (self):
        app = self.app or getattr (self.module, self.appname)
        self.has_life_cycle and app.life_cycle ("before_mount", self.wasc)

    def mounted (self):
        app = self.app or getattr (self.module, self.appname)
        self.has_life_cycle and app.life_cycle ("mounted", self.wasc ())
        self.has_life_cycle and app.life_cycle ("mounted_or_reloaded", self.wasc ())

    def before_umount (self):
        app = self.app or getattr (self.module, self.appname)
        self.has_life_cycle and app.life_cycle ("before_umount", self.wasc ())
        hasattr (self.app_initer, '__umount__') and self.wasc.execute_function (self.app_initer.__umount__, (app,))

    def umounted (self):
        app = self.app or getattr (self.module, self.appname)
        self.has_life_cycle and app.life_cycle ("umounted", self.wasc)
        hasattr (self.app_initer, '__umounted__') and self.wasc.execute_function (self.app_initer.__umounted__, (app,))

    def cleanup (self):
        app = self.app or getattr (self.module, self.appname)
        try: app.cleanup ()
        except AttributeError: pass

    def check_django_reloader (self, now):
        if self.django.reloaded ():
            self.wasc.logger ("app", "reloading app, %s" % self.abspath, "debug")
            self.last_reloaded = time.time ()
            lifetime.shutdown (3, 0)

    def set_devel_env (self, app):
        has_policy = False
        if hasattr (app, "ATILA_THE_HUN"):
            skitai_env = os.environ.get ("SKITAIENV")
            if skitai_env == "DEVEL":
                self.debug = app.debug = True
                self.use_reloader = app.use_reloader = True
                app.expose_spec = True
                has_policy = True
            elif skitai_env == "PRODUCTION":
                self.debug = app.debug = False
                self.use_reloader = app.use_reloader = False
                app.expose_spec = False
                has_policy = True

        if not has_policy:
            # inherit
            try: self.debug = app.debug
            except AttributeError: pass
            try: self.use_reloader = app.use_reloader
            except AttributeError: pass

        if self.use_reloader and self.django:
            lifetime.maintern.sched (1.0, self.check_django_reloader)

    def update_file_info (self):
        if self.module is None:
            # app directly mounted, cannot reload app
            return
        stat = os.stat (self.abspath)
        self.file_info = (stat.st_mtime, stat.st_size)

    def maybe_reload (self):
        if not self.use_reloader:
            return

        if self.django:
            # see check_django_reloader
            return

        if time.time () - self.last_reloaded < 1.0:
            return

        stat = os.stat (self.abspath)
        if self.file_info != (stat.st_mtime, stat.st_size):
            oldapp = self.app or getattr (self.module, self.appname)
            hasattr (self.app_initer, '__reload__') and self.wasc.execute_function (self.app_initer.__reload__, (oldapp,))
            self.has_life_cycle and oldapp.life_cycle ("before_reload", self.wasc ())

            try:
                if self.app_initer:
                    reload (self.app_initer)
                else:
                    reloaded = importer.reimporter (self.module, self.directory, self.libpath)
                    if not reloaded:
                        return
                    self.module, self.abspath = reloaded

            except:
                if self.app:
                    self.app = oldapp
                else:
                    setattr (self.module, self.appname, oldapp)
                raise

            if hasattr (oldapp, "remove_events"):
                oldapp.remove_events (self.bus)
            PRESERVED = []
            if hasattr (oldapp, "PRESERVES_ON_RELOAD"):
                PRESERVED = [(attr, getattr (oldapp, attr)) for attr in oldapp.PRESERVES_ON_RELOAD]

            self.start_app (reloded = True)
            if hasattr (self.module, '__app__'):
                newapp = self.module.__app__ ()
            else:
                newapp = getattr (self.module, self.appname)
            for attr, value in PRESERVED:
                setattr (newapp, attr, value)

            # reloaded
            hasattr (self.app_initer, '__reloaded__') and self.wasc.execute_function (self.app_initer.__reloaded__, (newapp,))
            self.has_life_cycle and newapp.life_cycle ("reloaded", self.wasc ())
            self.has_life_cycle and newapp.life_cycle ("mounted_or_reloaded", self.wasc ())
            self.last_reloaded = time.time ()
            self.wasc.logger ("app", "reloading app, %s" % self.abspath, "debug")

    def set_route (self, route):
        while route and route [-1] == "/":
            route = route [:-1]
        self.route = route + "/"
        self.route_len = len (self.route) - 1

    def get_route (self):
        return self.route

    def get_path_info (self, path):
        path_info = ("/" + path) [self.route_len:]
        return path_info

    def __call__ (self, env, start_response):
        self.use_reloader and self.maybe_reload ()
        app = self.app or getattr (self.module, self.appname)
        return app (env, start_response)


class ModuleManager:
    modules = {}
    def __init__(self, wasc, handler):
        self.wasc = wasc
        self.handler = handler
        self.modules = {}
        self.modnames = {}
        self.bus = evbus.EventBus (self.wasc.logger.get ('app'))
        if hasattr (wasc, "async_executor"):
            self.bus.set_event_loop (wasc.async_executor.loop)

    def __getitem__ (self, name):
        try:
            return self.modnames [name].get_callable ()
        except KeyError:
            raise NameError ('app `{}` not found'.format (name))

    def get (self, name, default = None):
        try:
            return self.modnames [name].get_callable ()
        except KeyError:
            return default

    def build_url (self, thing, *args, **kargs):
        a, b = thing.split (":", 1)
        return self.modnames [a].get_callable ().build_url (b, *args, **kargs)

    def add_module (self, route, directory, modname, pref, name):
        if isinstance (modname, tuple):
            if not name:
                name = '{}'.format (os.path.basename (modname [1][:-3]))
            modname, _path = modname
            directory = _path

        if not name:
            if isinstance (modname, str):
                name = os.path.join (directory, modname)
            elif hasattr (modname, '__app__'):
                name = modname.__name__.split (".", 1) [0]
            else:
                try:
                    name = '{}:{}'.format (modname.name.split (".", 1) [0], str (id (modname)) [:6])
                except AttributeError:
                    name = 'app:{}'.format (str (id (modname)) [:6])

        if name in self.modnames:
            self.wasc.logger ("app", "app name collision detected: %s" % tc.error (name), "error")
            return

        if not route:
            route = "/"
        elif not route.endswith ("/"):
            route = route + "/"

        try:
            module = Module (self.wasc, self.handler, self.bus, route, directory, modname, pref)
        except:
            self.wasc.logger ("app", "[error] app load failed: %s" % tc.error (os.path.basename (name)))
            raise
        else:
            self.wasc.logger ("app", "[info] app %s mounted to %s" % (tc.yellow (os.path.basename (name)), tc.white (route)))
            self.modnames [name] = module
            if route not in self.modules:
                self.modules [route] = [module]
            else:
                assert route == '/', "only root path can mount multiple apps"
                # first mount first priority, not-atila has last priority
                if not hasattr (self.modules [route][-1].get_callable (), "ATILA_THE_HUN"):
                    if not hasattr (module.get_callable (), "ATILA_THE_HUN"):
                        raise RuntimeError ("app route collision detected: %s to %s" % (route, module.abspath))
                    else:
                        self.modules [route].insert (len (self.modules [route]) - 1, module)
                else:
                    self.modules [route].append (module)

    def get_app (self, script_name):
        route = self.has_route (script_name)
        if route in (0, 1): # 404, 301
            return None

        try:
            apphs = self.modules [route]
        except KeyError:
            return None

        if len (apphs) == 1:
            return apphs [0]

        if script_name == '/' and '//' in self.modules:
            return self.modules ['//']

        path = script_name
        while path and path [0] == '/':
            path = path [1:]
        if '%' in path:
            path = unquote (path)

        for apph in apphs:
            path_info = apph.get_path_info (path)
            if not hasattr (apph.get_callable (), 'ATILA_THE_HUN') or apph.get_callable ().find_method (path_info, '__proto__') [-1] != 404:
                # auto mapping to top-level path
                if script_name == '/':
                    self.modules ['//'] = apph
                else:
                    basepath = "/" + script_name [1:].split ('/') [0]
                    self.modules [basepath] = [apph]
                return apph
        return None # 404

    def has_route (self, script_name):
        # 0: 404
        # 1: 301 => /skitai => /skitai/
        if script_name == "/" and "/" in self.modules:
            return "/"

        cands = []
        for route in self.modules:
            if script_name == route:
                cands.append (route)
            elif script_name + "/" == route:
                return 1
            elif script_name.startswith (route [-1] != "/" and route + "/" or route):
                cands.append (route)

        if cands:
            if len (cands) == 1:
                return cands [0]
            cands.sort (key = lambda x: len (x))
            return cands [-1]

        elif "/" in self.modules:
            return "/"

        return 0

    def unload (self, route):
        module = self.modules [route]
        self.wasc.logger ("app", "[info] unloading app: %s" % route)
        try:
            self.wasc.logger ("app", "[info] ..cleanup app: %s" % route)
            module.cleanup ()
        except AttributeError:
            pass
        except:
            self.wasc.logger.trace ("app")
        del module
        del self.modules [route]

    def cleanup (self):
        self.wasc.logger ("app", "[info] cleanup apps")
        for route, module in list(self.modules.items ()):
            try:
                self.wasc.logger ("app", "[info] ..cleanup app: %s" % route)
                module.cleanup ()
            except AttributeError:
                pass
            except:
                self.wasc.logger.trace ("app")

    def status (self):
        d = {}
        for path, module in list(self.modules.items ()):
            if not isinstance (module, list):
                module = [module]
            for m in module:
                d ['<a href="%s">%s</a>' % (path, path)] = m.abspath
        return d


