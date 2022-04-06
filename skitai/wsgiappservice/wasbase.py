import os, sys
import time
from hmac import new as hmac
import copy
from hashlib import sha1, md5
import json
import xmlrpc.client as xmlrpclib
import base64
import pickle
import random
import threading
from rs4 import logger
from rs4.webkit import jwt
from ..protocols.sock.impl.http import http_date, util
from skitai import __version__, WS_EVT_OPEN, WS_EVT_CLOSE, WS_EVT_INIT, NAME, DEFAULT_BACKGROUND_TASK_TIMEOUT
from skitai import lifetime
from ..wastuff import server_info
from ..backbone import http_response
from ..wastuff.triple_logger import Logger
if os.environ.get ("SKITAIENV") == "PYTEST":
    from threading import RLock
else:
    from multiprocessing import RLock
import skitai
import xmlrpc.client as xmlrpclib
from ..wastuff.api import API
if os.environ.get ("SKITAIENV") == "PYTEST":
    from ..wastuff.semaps import TestSemaps as Semaps
else:
    from ..wastuff.semaps import Semaps
from .wastype import _WASType
from rs4.attrdict import AttrDictTS
import asyncio

workers_shared_mmap = Semaps ([], "d", 256)

class WASBase (_WASType):
    _luwatcher = workers_shared_mmap
    _process_locks = [RLock () for i in range (8)]

    version = __version__
    ID = None # set by skitai.was
    g = AttrDictTS ()
    objects = {}
    lock = plock = RLock ()
    init_time = time.time ()
    cloned = False

    @classmethod
    def get_lock (cls, name = "__main__"):
        return cls._process_locks [hash (name) % 8]

    # application friendly methods -----------------------------------------
    @classmethod
    def register (cls, name, obj):
        if hasattr (cls, name):
            raise AttributeError ("server object `%s` is already exists" % name)
        cls.objects [name] = obj
        setattr (cls, name, obj)

    @classmethod
    def unregister (cls, name):
        del cls.objects [name]
        return delattr (cls, name)

    @classmethod
    def add_handler (cls, back, handler, *args, **karg):
        h = handler (cls, *args, **karg)
        if hasattr (cls, "httpserver"):
            cls.httpserver.install_handler (h, back)
        return h

    @classmethod
    def cleanup (cls, phase = 0):
        for attr, obj in list (cls.objects.items ()):
            if attr in ("logger", "async_executor"):
                if phase == 1:
                    continue

            if attr == "clusters":
                cls.logger ("server", "[info] cleanup %s" % attr)
                for name, cluster in obj.items ():
                    cluster.cleanup ()
                continue

            if hasattr (obj, "cleanup"):
                try:
                    cls.logger ("server", "[info] cleanup %s" % attr)
                    obj.cleanup ()
                except:
                    cls.logger.trace ("server")

            del cls.objects [attr]
            del obj

    @classmethod
    def execute_function (cls, func, args = (), kargs = {}):
        r = func (*args, **kargs)
        if not asyncio.iscoroutine (r):
            return r
        future = asyncio.run_coroutine_threadsafe (r, cls.async_executor.loop)
        if future.exception ():
            raise future.exception ()
        return future.result ()

    def _clone (self, disposable = False):
        new_env = {}
        if hasattr (self, 'env'):
            new_env = copy.copy (self.env)
            try:
                self.env.pop ('wsgi.input') # depending closure
            except KeyError:
                pass

        new_was = skitai.was._new () if disposable else skitai.was._get (True) # get clone was
        new_env ["skitai.was"] = new_was
        new_was.env = new_env

        # cloning
        for attr in ('request', 'app', 'apps', 'subapp', 'response', 'websocket'):
            try:
                val = getattr (self, attr)
            except AttributeError:
                try: delattr (new_was, attr)
                except AttributeError: pass
            else:
                setattr (new_was, attr, val)
        return new_was

    @property
    def timestamp (self):
        return int (time.time () * 1000)

    @property
    def uniqid (self):
        return "{}{}".format (self.timestamp, self.gentemp () [-7:])

    def __dir__ (self):
        objs = list (self.objects.keys ()) + ["env", "app", "apps"]
        hasattr (self, "request") and objs.append ("request")
        hasattr (self, "response") and objs.append ("response")
        return objs

    def __str__ (self):
        return "skitai was for {}".format (threading.currentThread ())

    def in__dict__ (self, name):
        return name in self.__dict__

    # utils -----------------------------------------------
    def txnid (self):
        return "%s/%s" % (self.request.gtxid, self.request.ltxid)

    def rebuild_header (self, header, method, data = None, internal = True):
        nheader = util.normheader (header)
        if method in {"get", "delete", "post", "put", "patch", "upload"}:
            try:
                default_request_type = self.app.config.get ("default_request_type")
            except AttributeError:
                default_request_type = None
            if not default_request_type:
                default_request_type = self.DEFAULT_REQUEST_TYPE
            util.set_content_types (nheader, data, default_request_type)

        if internal:
            nheader ["X-Gtxn-Id"] = self.request.get_gtxid ()
            nheader ["X-Ltxn-Id"] = self.request.get_ltxid (1)
        else:
            nheader ["X-Requested-With"] = NAME
        return nheader

    # system functions ----------------------------------------------
    def log (self, msg, category = "info", at = "app"):
        self.logger (at, msg, "%s:%s" % (category, self.txnid ()))

    def traceback (self, id = "", at = "app"):
        if not id:
            id = self.txnid ()
        self.logger.trace (at, id)

    # server management, only allpy to current worker process
    def status (self, flt = None, fancy = True):
        return server_info.make (self, flt, fancy)

    def restart (self, timeout = 0):
        lifetime.shutdown (3, timeout)

    def shutdown (self, timeout = 0):
        lifetime.shutdown (0, timeout)

    # process scoped caching utils --------------------------
    def setlu (self, name, *args, **karg):
        self._luwatcher.set (name, time.time (), karg.get ("x_ignore", False))
        hasattr (self, 'app') and self.app and self.app.emit ('setlu:' + name, *args, **karg)

    def getlu (self, *names):
        mtimes = []
        for name in names:
            mtime = self._luwatcher.get (name, self.init_time)
            mtimes.append (mtime)
        return max (mtimes)

    # http23 --------------------------------------------------
    def push (self, uri):
        self.request.response.push_promise (uri)

    # websocket ----------------------------------------------
    def wsconfig (self, spec, timeout = 60, encoding = "text", session = None):
        # other than atila, encoding became varname
        self.env ["websocket.config"] = (spec, timeout, encoding, session)
        return ""

    def wsinit (self):
        return self.env.get ('websocket.event') == WS_EVT_INIT

    def wsopened (self):
        return self.env.get ('websocket.event') == WS_EVT_OPEN

    def wsclosed (self):
        return self.env.get ('websocket.event') == WS_EVT_CLOSE

    def wshasevent (self):
        return self.env.get ('websocket.event')

    def wsclient (self):
        return self.env.get ('websocket.client')
