import os, sys
import time
import tempfile
from hmac import new as hmac
from hashlib import sha1
import json
import xmlrpc.client as xmlrpclib
import base64
import pickle
import random
import threading
from rs4 import pathtool, logger, jwt, deco
from aquests.protocols.smtp import composer
from aquests.protocols.http import http_date, util
from skitai import __version__, WS_EVT_OPEN, WS_EVT_CLOSE, WS_EVT_INIT, NAME
from skitai import lifetime
from . import server_info
from .. import http_response
from .promise import Promise
from .futures import Futures
from .triple_logger import Logger
from . import django_adaptor
if os.environ.get ("SKITAI_ENV") == "PYTEST":
    from threading import RLock    
else:    
    from multiprocessing import RLock

from rs4.producers import file_producer
from .api import DateEncoder

if os.name == "nt":
    TEMP_DIR =  os.path.join (tempfile.gettempdir(), "skitai-gentemp")
else:
    TEMP_DIR = "/var/tmp/skitai-gentemp"        
pathtool.mkdir (TEMP_DIR)
      
class JWTUser:
    def __init__ (self, claims):
        self.__claims = claims
    
    @property
    def name (self):
        return self.__claims ["username"]
        
    def __getattr__ (self, attr):
        return self.__claims.get (attr)
            
    def __str__ (self):
        return self.name

class WASBase:
    version = __version__    
    objects = {}    
    _luwatcher = None
    _stwatcher = None
    
    lock = plock = RLock ()
    init_time = time.time ()    
    
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
    
    # mehiods remap ------------------------------------------------
    def __getattr__ (self, name):
        if self.in__dict__ ("app"): # atila app
            attr = self.app.create_on_demand (self, name)
            if attr:
                setattr (self, name, attr)
                return attr
        
        try:
            return self.objects [name]
        except KeyError:    
            raise AttributeError ("'was' hasn't attribute '%s'" % name)    
    
    # TXN -----------------------------------------------
    
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
    
    @property
    def tempfile (self):
        return self.gentemp () 
    
    def gentemp (self):
        return os.path.join (TEMP_DIR, next (tempfile._get_candidate_names()))
    
    # -- only allpy to current worker process
    def status (self, flt = None, fancy = True):        
        return server_info.make (self, flt, fancy)
    
    def restart (self, timeout = 0):
        lifetime.shutdown (3, timeout)
    
    def shutdown (self, timeout = 0):
        lifetime.shutdown (0, timeout)
    
    # URL builders -------------------------------------------------
    def urlfor (self, thing, *args, **karg):
        # override with resource default args
        if not isinstance (thing, str) or thing.startswith ("/") or thing.find (":") == -1:
            return self.app.urlfor (thing, *args, **karg)        
        return self.apps.urlfor (thing, *args, **karg)    
    ab = urlfor
    
    def partial (self, thing, **karg):
        # override with current args
        karg ["__defaults__"] = self.request.args
        return self.ab (thing, **karg)
    
    def baseurl (self, thing):
        # resource path info without parameters
        return self.ab (thing, __resource_path_only__ = True)
    basepath = baseurl
    
    # response helpers --------------------------------------------
        
    def render (self, template_file, _do_not_use_this_variable_name_ = {}, **karg):
        return self.app.render (self, template_file, _do_not_use_this_variable_name_, **karg)
    
    REDIRECT_TEMPLATE =  (
        "<html><head><title>%s</title></head>"
        "<body><h1>%s</h1>"
        "This document may be found " 
        '<a HREF="%s">here</a></body></html>'
    )
    def redirect (self, url, status = "302 Object Moved", body = None, headers = None):
        redirect_headers = [
            ("Location", url), 
            ("Cache-Control", "max-age=0"), 
            ("Expires", http_date.build_http_date (time.time ()))
        ]
        if type (headers) is list:
            redirect_headers += headers
        if not body:
            body = self.REDIRECT_TEMPLATE % (status, status, url)            
        return self.response (status, body, redirect_headers)
    
    def futures (self, reqs, **args):
        return Futures (self._clone (), reqs, **args)
        
    def email (self, subject, snd, rcpt):
        if composer.Composer.SAVE_PATH is None:
            composer.Composer.SAVE_PATH = os.path.join ("/var/tmp/skitai", "smtpda", "spool")
            pathtool.mkdir (composer.Composer.SAVE_PATH)
        return composer.Composer (subject, snd, rcpt)
    
    # event -------------------------------------------------
    
    def broadcast (self, event, *args, **kargs):
        return self.apps.bus.emit (event, self, *args, **kargs)
    
    def setlu (self, name, *args, **karg):
        self._luwatcher.set (name, time.time (), karg.get ("x_ignore", False))
        self.broadcast (name, *args, **karg)            
        
    def getlu (self, *names):
        mtimes = []
        for name in names:
            mtime = self._luwatcher.get (name, self.init_time)
            mtimes.append (mtime)
        return max (mtimes)
    
    def setgs (self, name, v, *args, **kargs):
        assert isinstance (v, int) 
        self._stwatcher.set (name, time.time ())
        self.broadcast (name, v, *args, **karg)            
        
    def getgs (self, *names):
        mtimes = []
        for name in names:
            mtime = self._stwatcher.get (name, self.init_time)
            mtimes.append (mtime)
        return max (mtimes)
    
    # JWT token --------------------------------------------------
    def mkjwt (self, claim, alg = "HS256"):
        assert "exp" in claim, "exp claim required"            
        return jwt.gen_token (self.app.salt, claim, alg)
        
    def dejwt (self, token = None):
        if not token:
            token_ = self.request.get_header ("authorization")
            if not token_ or token_ [:7].lower () != "bearer ":
                return
            token = token_ [7:]
            
        try: 
            claims = jwt.get_claim (self.app.salt, token)
        except (TypeError, ValueError): 
            return {"err": "invalid token"}
        if claims is None:
            return {"err": "invalid signature"}
        now = time.time ()
        if claims ["exp"] < now:
            return {"err": "token expired"}
        if "nbf" in claims and claims ["nbf"] > now:
            return {"err": "token not activated yet"}
        if "username" in claims:
            self.request.user = JWTUser (claims)
        self.request.JWT = claims    
        return claims
        
    # simple/session token  ----------------------------------------
    def _unserialize_token (self, string):
        def adjust_padding (s):
            paddings = 4 - (len (s) % 4)
            if paddings != 4:
                s += ("=" * paddings)
            return s
        
        string = string.replace (" ", "+")
        try:
            base64_hash, data = string.split('?', 1)
        except ValueError:
            return    
        client_hash = base64.b64decode(adjust_padding (base64_hash))
        data = base64.b64decode(adjust_padding (data))
        mac = hmac (self.app.salt, None, sha1)        
        mac.update (data)
        if client_hash != mac.digest():
            return
        return pickle.loads (data)
    
    def mkott (self, obj, timeout = 1200, session_key = None):
        wrapper = {
            'object': obj,
            'timeout': time.time () + timeout
        }
        if session_key:
            token = hex (random.getrandbits (64))
            tokey = '_{}_token'.format (session_key)
            wrapper ['_session_token'] = (tokey, token)
            self.session [tokey] = token
            
        data = pickle.dumps (wrapper, 1)
        mac = hmac (self.app.salt, None, sha1)
        mac.update (data)
        return (base64.b64encode (mac.digest()).strip().rstrip (b'=') + b"?" + base64.b64encode (data).strip ().rstrip (b'=')).decode ("utf8")
    
    def deott (self, string):
        wrapper = self._unserialize_token (string)
        if not wrapper:
            return 
        
        # validation with session
        tokey = None
        has_error = False
        if wrapper ['timeout']  < time.time ():
            has_error = True

        if not has_error:
            session_token = wrapper.get ('_session_token')
            if session_token:
                # verify with session                
                tokey, token = session_token    
                if token != self.session.get (tokey):
                    has_error = True
                    
        if has_error:
            if tokey:
                del self.session [tokey]
            return
        
        obj = wrapper ['object']
        return obj
    
    def rvott (self, string):
        # revoke token
        wrapper = self._unserialize_token (string)
        session_token = wrapper.get ('_session_token')
        if not session_token:
            return
        tokey, token = session_token
        if not self.session.get (tokey):
            return
        del self.session [tokey]
    
    mktoken = token = mkott
    rmtoken = rvott
    detoken = deott
        
    # CSRF token ------------------------------------------------------    
    CSRF_NAME = "_csrf_token"
    @property
    def csrf_token (self):
        if self.CSRF_NAME not in self.session:
            self.session [self.CSRF_NAME] = hex (random.getrandbits (64))
        return self.session [self.CSRF_NAME]

    @property
    def csrf_token_input (self):
        return '<input type="hidden" name="{}" value="{}">'.format (self.CSRF_NAME, self.csrf_token)
    
    def csrf_verify (self, keep = False):
        if not self.request.args.get (self.CSRF_NAME):
            return False
        token = self.request.args [self.CSRF_NAME]
        if self.csrf_token == token:
            if not keep:
                del self.session [self.CSRF_NAME]
            return True
        return False
    
    # proxy & adaptor  -----------------------------------------------
    @property
    def sql (self):
        return self.app.sqlphile
    
    @property
    def django (self):
        if hasattr (self.request, "django"):
            return self.request.django
        self.request.django = django_adaptor.request (self)
        return self.request.django
    
    # websocket methods for generic WSGI containers ------------------
    def wsconfig (self, spec, timeout = 60, encoding = "text"):
        self.env ["websocket.config"] = (spec, timeout, encoding)
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

    # will be deprecated ----------------------------------------------
    @deco.deprecated
    def promise (self, handler, **karg):
        self.response.set_streaming ()
        return Promise (self, handler, **karg)
    
    @deco.deprecated    
    def togrpc (self, obj):
        return obj.SerializeToString ()
    
    @deco.deprecated
    def fromgrpc (self, message, obj):
        return message.ParseFromString (obj)
    
    @deco.deprecated    
    def tojson (self, obj):
        return json.dumps (obj, cls = DateEncoder)
    
    @deco.deprecated    
    def toxml (self, obj):
        return xmlrpclib.dumps (obj, methodresponse = False, allow_none = True, encoding = "utf8")    
    
    @deco.deprecated
    def fromjson (self, obj):
        if type (obj) is bytes:
            obj = obj.decode ('utf8')
        return json.loads (obj)
    
    @deco.deprecated
    def fromxml (self, obj, use_datetime = 0):
        return xmlrpclib.loads (obj)
    
    @deco.deprecated
    def fstream (self, path, mimetype = 'application/octet-stream'):    
        self.response.set_header ('Content-Type',  mimetype)
        self.response.set_header ('Content-Length', str (os.path.getsize (path)))    
        return file_producer (open (path, "rb"))
    
    @deco.deprecated        
    def jstream (self, obj, key = None):
        self.response.set_header ("Content-Type", "application/json")
        if key:
            # for single skeleton data is not dict
            return self.tojson ({key: obj})
        else:
            return self.tojson (obj)        
    
    @deco.deprecated
    def xstream (self, obj, use_datetime = 0):            
        self.response.set_header ("Content-Type", "text/xml")
        return self.toxml (obj, use_datetime)
    
    @deco.deprecated
    def gstream (self, obj):
        self.response.set_header ("Content-Type", "application/grpc")
        return self.togrpc (obj)
    
    @deco.deprecated
    def render_ei (self, exc_info, format = 0):
        return http_response.catch (format, exc_info)

