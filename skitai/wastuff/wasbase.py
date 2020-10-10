import os, sys
import time
import tempfile
from hmac import new as hmac
import copy
from hashlib import sha1, md5
import json
import xmlrpc.client as xmlrpclib
import base64
import pickle
import random
import threading
from rs4 import pathtool, logger, deco
from rs4.webkit import jwt
from aquests.protocols.smtp import composer
from aquests.protocols.http import http_date, util
from skitai import __version__, WS_EVT_OPEN, WS_EVT_CLOSE, WS_EVT_INIT, NAME, DEFAULT_BACKGROUND_TASK_TIMEOUT
from skitai import lifetime
from . import server_info
from ..corequest import corequest, tasks
from ..corequest.pth import sp_task
from ..backbone import http_response
from .triple_logger import Logger
if os.environ.get ("SKITAIENV") == "PYTEST":
    from threading import RLock
else:
    from multiprocessing import RLock
from skitai import was as the_was
import xmlrpc.client as xmlrpclib
from rs4.producers import file_producer
from .api import API
from rs4.annotations import deprecated
from .api import tojson
if os.environ.get ("SKITAIENV") == "PYTEST":
    from .semaps import TestSemaps as Semaps
else:
    from .semaps import Semaps

if os.name == "nt":
    TEMP_DIR =  os.path.join (tempfile.gettempdir(), "skitai-gentemp")
else:
    TEMP_DIR = "/var/tmp/skitai/__gentemp"
pathtool.mkdir (TEMP_DIR)

composer.Composer.SAVE_PATH = os.path.join ("/var/tmp/skitai", "smtpda", "spool")
pathtool.mkdir (composer.Composer.SAVE_PATH)

class WASBase:
    version = __version__
    ID = None # set by skitai.was
    objects = {}
    _luwatcher = Semaps ([], "d", 256)
    lock = plock = RLock ()
    init_time = time.time ()
    cloned = False
    _process_locks = [RLock () for i in range (8)]

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

    def _clone (self):
        new_env = {}
        if hasattr (self, 'env'):
            new_env = copy.copy (self.env)
            self.env.pop ('wsgi.input') # depending closure
        new_was = the_was._get (True) # get clone was
        new_env ["skitai.was"] = new_was
        new_was.env = new_env

        # cloning
        for attr in ('request', 'app', 'apps', 'subapp', 'response'):
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
        return self.objects.keys ()

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

    # concurrencies ----------------------------------------------
    def Thread (self, target, *args, **kargs):
        # also can be Thread (target, args, kwargs, meta)
        return self.executors.create_thread (self.ID, target, *args, **kargs)

    def Process (self, target, *args, **kargs):
        return self.executors.create_process (self.ID, target, *args, **kargs)

    def Subprocess (self, cmd, meta = None, filter = None, timeout = DEFAULT_BACKGROUND_TASK_TIMEOUT):
        return sp_task.Task (cmd, self._set_was_id (meta), filter, timeout)

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

    # system functions ----------------------------------------------
    def log (self, msg, category = "info", at = "app"):
        self.logger (at, msg, "%s:%s" % (category, self.txnid ()))

    def traceback (self, id = "", at = "app"):
        if not id:
            id = self.txnid ()
        self.logger.trace (at, id)

    def render_ei (self, exc_info, format = 0):
        return http_response.catch (format, exc_info)

    @property
    def tempfile (self):
        return self.gentemp ()

    @property
    def flashfile (self):
        return pathtool.FlashFile (self.gentemp ())

    def gentemp (self):
        return os.path.join (TEMP_DIR, next (tempfile._get_candidate_names()))

    def email (self, subject, snd, rcpt):
        return composer.Composer (subject, snd, rcpt)

    # -- only allpy to current worker process
    def status (self, flt = None, fancy = True):
        return server_info.make (self, flt, fancy)

    def restart (self, timeout = 0):
        lifetime.shutdown (3, timeout)

    def shutdown (self, timeout = 0):
        lifetime.shutdown (0, timeout)

    # inter-processes communication ------------------------------
    def setlu (self, name, *args, **karg):
        self._luwatcher.set (name, time.time (), karg.get ("x_ignore", False))
        self.broadcast (name, *args, **karg)

    def getlu (self, *names):
        mtimes = []
        for name in names:
            mtime = self._luwatcher.get (name, self.init_time)
            mtimes.append (mtime)
        return max (mtimes)

    def setgs (self, name, val):
        assert isinstance (val, int), "global state must be integer"
        self._luwatcher.set (name, val)
        self.broadcast (name, val)

    def getgs (self, name, default = 0):
        assert isinstance (default, int), "global state must be integer"
        val = self._luwatcher.get (name, default)
        return int (val)

    def incgs (self, name, delta = 1):
        val = self.getgs (name) + delta
        self.setgs (name, val)

    # websokcet / http2 ------------------------------------------
    def push (self, uri):
        self.request.response.push_promise (uri)

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

    # will be deprecated --------------------------------------------------
    @deprecated ()
    def togrpc (self, obj):
        return obj.SerializeToString ()

    @deprecated ()
    def fromgrpc (self, message, obj):
        return message.ParseFromString (obj)

    @deprecated ()
    def tojson (self, obj):
        return tojson (obj)
        # return json.dumps (obj, cls = encoder)

    @deprecated ()
    def toxml (self, obj):
        return xmlrpclib.dumps (obj, methodresponse = False, allow_none = True, encoding = "utf8")

    @deprecated ()
    def fromjson (self, obj):
        if type (obj) is bytes:
            obj = obj.decode ('utf8')
        return json.loads (obj)

    @deprecated ()
    def fromxml (self, obj, use_datetime = 0):
        return xmlrpclib.loads (obj)

    @deprecated ()
    def fstream (self, path, mimetype = 'application/octet-stream'):
        self.response.set_header ('Content-Type',  mimetype)
        self.response.set_header ('Content-Length', str (os.path.getsize (path)))
        return file_producer (open (path, "rb"))

    @deprecated ()
    def jstream (self, obj, key = None):
        self.response.set_header ("Content-Type", "application/json")
        if key:
            # for single skeleton data is not dict
            return self.tojson ({key: obj})
        else:
            return self.tojson (obj)

    @deprecated ()
    def xstream (self, obj, use_datetime = 0):
        self.response.set_header ("Content-Type", "text/xml")
        return self.toxml (obj, use_datetime)

    @deprecated ()
    def gstream (self, obj):
        self.response.set_header ("Content-Type", "application/grpc")
        return self.togrpc (obj)

    @deprecated ('use corequest.then ()')
    def Future (self, req, timeout = 10, **args):
        # deprecated, use corequest.then ()
        if isinstance (req, (list, tuple)):
            raise ValueError ('Future should be single corequest')
        return tasks.Future (req, timeout, **args)

    @deprecated ('use was.Tasks.then ()')
    def Futures (self, reqs, timeout = 10, **args):
        if not isinstance (reqs, (list, tuple)):
            raise ValueError ('Futures should be multiple corequests')
        return tasks.Futures (reqs, timeout, **args)
    future = Future
    futures = Futures
