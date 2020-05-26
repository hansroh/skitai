import time
from aquests.athreads import socket_map
from aquests.athreads import trigger
from rs4.cbutil import tuple_cb
from aquests.client.asynconnect import AsynSSLConnect, AsynConnect
from aquests.dbapi.dbconnect import DBConnect
import threading
from aquests.protocols.http import request as http_request
from aquests.protocols.http import request_handler as http_request_handler
from aquests.protocols.http2 import request_handler as http2_request_handler
from aquests.protocols.grpc.request import GRPCRequest
from aquests.protocols.http import response as http_response
from aquests.protocols.ws import request_handler as ws_request_handler
from aquests.protocols.ws import request as ws_request
from . import rcache
from skitai import lifetime
from aquests import asyncore
import sys
import inspect
from skitai import exceptions
from skitai import REQFAIL, UNSENT, TIMEOUT, NETERR, NORMAL
from ...corequest import corequest, response
import sqlite3

try:
    import psycopg2
except ImportError:
    class PGIntegrityError (Exception):
        pass
else:
    PGIntegrityError = psycopg2.IntegrityError

DEFAULT_TIMEOUT = 10
WAIT_POLL = False

class OperationError (Exception):
    pass


class Result (response, rcache.Result):
    def __init__ (self, id, status, response, ident = None):
        rcache.Result.__init__ (self, status, ident)
        self.node = id
        self.__response = response

    def __getattr__ (self, attr):
        return getattr (self.__response, attr)

    def reraise (self):
        if self.status_code >= 300:
            try:
                self.__response.expt
            except AttributeError:
                # redircting to HTTPError
                raise exceptions.HTTPError ("%d %s" % (self.status_code, self.reason))
            else:
                self.__response.raise_for_status ()
        return self

    def close (self):
        self.__response = None

    def cache (self, timeout = 60, cache_if = (200,)):
        if not timeout:
            return
        if self.status != NORMAL or self.status_code not in cache_if:
            return
        rcache.Result.cache (self, timeout)
        return self

    def fetch (self, cache = None, cache_if = (200,), one = False):
        self.reraise ()
        self.cache (cache, cache_if)
        if one:
            if len (self.data) == 0:
                raise exceptions.HTTPError ("410 Partial Not Found")
            if len (self.data) != 1:
                raise exceptions.HTTPError ("409 Conflict")
            if isinstance (self.data, dict):
                return self.data.popitem () [1]
            return self.data [0]
        return self.data

    def one (self, cache = None, cache_if = (200,)):
        try:
            return self.fetch (cache, cache_if, True)
        except (PGIntegrityError, sqlite3.IntegrityError):
            # primary or unique index error
            raise exceptions.HTTPError ("409 Conflict")

    def commit (self):
        self.reraise ()


class Results (response, rcache.Result):
    def __init__ (self, results, ident = None):
        self.results = results
        self.status_code = [rs.status_code for rs in results]
        rcache.Result.__init__ (self, [rs.status for rs in self.results], ident)

    def __iter__ (self):
        return self.results.__iter__ ()

    @property
    def data (self):
        return [r.data for r in self.results]

    @property
    def text (self):
        return [r.text for r in self.results]

    def reraise (self):
        [r.reraise () for r in self.results]

    def cache (self, timeout = 60, cache_if = (200,)):
        if [_f for _f in [rs.status != NORMAL or rs.status_code not in cache_if for rs in self.results] if _f]:
            return
        rcache.Result.cache (self, timeout)
        return self

    def fetch (self, cache = None, cache_if = (200,)):
        self.cache (cache, cache_if)
        return [r.fetch () for r in self.results]

    def one (self, cache = None, cache_if = (200,)):
        self.cache (cache, cache_if)
        return [r.one () for r in self.results]



class Dispatcher:
    def __init__ (self, cv, id, ident = None, filterfunc = None, cachefs = None, callback = None):
        self._cv = cv
        self.id = id
        self.ident = ident
        self.filterfunc = filterfunc
        self.cachefs = cachefs
        self.callback = callback
        self.creation_time = time.time ()
        self.status = UNSENT
        self.result = None
        self.handler = None

    def get_id (self):
        return self.id

    def get_status (self):
        with self._cv:
            return self.status

    def request_failed (self):
        self.status = REQFAIL
        tuple_cb (self, self.callback)

    def set_status (self, code, result = None):
        with self._cv:
            self.status = code
            if result:
                self.result = result
        return code

    def get_result (self):
        if not self.result:
            if self.get_status () == REQFAIL:
                self.result = Result (self.id, REQFAIL, http_response.FailedResponse (731, "Request Failed"), self.ident)
            else:
                self.result = Result (self.id, TIMEOUT, http_response.FailedResponse (730, "Timeout"), self.ident)
        return self.result

    def do_filter (self):
        if self.filterfunc:
            self.filterfunc (self.result)

    def handle_cache (self, response):
        self.set_status (NORMAL, Result (self.id, status, response, self.ident))

    def handle_result (self, handler):
        if self.get_status () == TIMEOUT:
            # timeout, ignore
            return

        response = handler.response
        # DON'T do_filter here, it blocks select loop
        if response.code >= 700:
            if response.code == 702:
                status = TIMEOUT
            else:
                status = NETERR
        else:
            status = NORMAL

        result = Result (self.id, status, response, self.ident)

        cakey = response.request.get_cache_key ()
        if self.cachefs and cakey and response.max_age:
            self.cachefs.save (
                cakey,
                response.get_header ("content-type"), response.content,
                response.max_age, 0
            )

        handler.callback = None
        handler.response = None
        self.set_status (status, result)
        tuple_cb (self, self.callback)


class FakeCondition:
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def acquire (self):
        pass
    wait = release = acquire


class Task (corequest):
    DEFAULT_CACHE_TIMEOUT = 42
    proto_map = dict (
       rpc = http_request.XMLRPCRequest,
       xmlrpc = http_request.XMLRPCRequest,
       jsonrpc = http_request.JSONRPCRequest,
       grpc = GRPCRequest
    )
    def __init__ (
            self,
            cluster,
            uri,
            params = None,
            reqtype = "get",
            headers = None,
            auth = None,
            meta = None,
            use_cache = False,
            mapreduce = True,
            filter = None,
            callback = None,
            cache = None,
            timeout = 10,
            origin = None,
            cachefs = None,
            logger = None
        ):

        self._uri = uri
        self._params = params
        self._headers = headers
        self._reqtype = reqtype
        self._auth = auth
        self.set_defaults (cluster, meta, use_cache, mapreduce, filter, callback, cache, timeout, origin, logger, cachefs)

        if not self._reqtype.lower ().endswith ("rpc"):
            self._build_request ("", self._params)

    @classmethod
    def add_proto (cls, name, class_):
        cls.proto_map [name] = class_

    def set_defaults (self, cluster, meta, use_cache, mapreduce, filter, callback, cache, timeout, origin, logger, cachefs = None):
        self._cluster = cluster
        self._meta = meta or {}
        self._use_cache = use_cache
        self._mapreduce = mapreduce
        self._filter = filter
        self._callback = callback
        self._cache_timeout = cache
        self._timeout = timeout
        self._origin = origin
        self._cachefs = cachefs
        self._logger = logger
        self._requests = {}
        self._results = []
        self._canceled = False
        self._init_time = time.time ()
        self._cv = None
        self._retry = 0
        self._numnodes = 0
        self._cached_result = None
        self._cached_request_args = None
        self._request = None
        self._ccv = None

        if self._cluster:
            nodes = self._cluster.get_nodes ()
            self._numnodes = len (nodes)
            if self._mapreduce:
                self._nodes = nodes
            else: # anyone of nodes
                self._nodes = [None]

    def __del__ (self):
        self._cv = None
        self._results = []

    def _get_ident (self):
        cluster_name = self._cluster.get_name ()
        if cluster_name == "__socketpool__":
            _id = "%s/%s" % (self._uri, self._reqtype)
        else:
            _id = "%s/%s/%s" % (cluster_name, self._uri, self._reqtype)
        _id += "/%s/%s" % self._cached_request_args
        _id += "%s" % (
            self._mapreduce and "/M" or ""
            )
        return _id

    def _add_header (self, n, v):
        if self._headers is None:
            self._headers = {}
        self._headers [n] = v

    def find_cache (self, request, rs, asyncon):
        if not self._cachefs:
            return False

        # IMP: mannual address setting
        request.set_address (asyncon.address)
        cakey = request.get_cache_key ()
        if not cakey:
            return False

        cachable = self._cachefs.is_cachable (
            request.method,
            request.get_header ("cache-control"),
            request.get_header ("cookie") is not None,
            request.get_header ("authorization") is not None,
            request.get_header ("pragma")
        )

        if not cachable:
            return False

        hit, compressed, max_age, content_type, content = self._cachefs.get (cakey, undecompressible = 0)
        if not hit:
            return False

        header = "HTTP/1.1 200 OK\r\nContent-Type: %s\r\nX-Skitaid-Cache-Lookup: %s" % (
            content_type, hit == 1 and "MEM_HIT" or "HIT"
        )
        response = http_response.Response (request, header)
        response.collect_incoming_data (content)
        response.done ()
        asyncon.set_active (False)
        rs.handle_cache (response)
        return True

    def _build_request (self, method, params):
        self._cached_request_args = (method, params) # backup for retry
        if self._use_cache and rcache.the_rcache:
            self._cached_result = rcache.the_rcache.get (self._get_ident (), self._use_cache)
            if self._cached_result is not None:
                self._cached_result.meta = self._meta
                self._callback and tuple_cb (self._cached_result, self._callback)
                return
            else:
                self._use_cache = False

        requests = 0
        while self._avails ():
            if self._cluster.get_name () != "__socketpool__":
                asyncon = self._get_connection (None)
            else:
                asyncon = self._get_connection (self._uri)

            self._auth = self._auth or asyncon.get_auth ()
            _reqtype = self._reqtype.lower ()
            rs = Dispatcher (
                self._cv, asyncon.address,
                ident = not self._mapreduce and self._get_ident () or None,
                filterfunc = self._filter, cachefs = self._cachefs,
                callback = self._collect
            )
            self._requests [rs] = asyncon
            args = (params, self._headers, self._auth, self._logger, self._meta)
            try:
                if _reqtype in ("ws", "wss"):
                    handler = ws_request_handler.RequestHandler
                    request = ws_request.Request (self._uri, *args)
                else:
                    if not self._use_cache:
                        self._add_header ("Cache-Control", "no-cache")
                    handler = http_request_handler.RequestHandler
                    try:
                        class_ = self.proto_map [_reqtype]
                    except KeyError:
                        if _reqtype == "upload":
                            request = http_request.HTTPMultipartRequest (self._uri, _reqtype, *args)
                        else:
                            request = http_request.HTTPRequest (self._uri, _reqtype, *args)
                    else:
                        request = class_ (self._uri, method, *args)

                if self.find_cache (request, rs, asyncon):
                    continue

            except:
                self.handle_request_failed (rs, asyncon, 'handler')
                continue

            try:
                asyncon.execute (request, rs, handler, self.handle_request_failed)
            except:
                self.handle_request_failed (rs, asyncon)
                continue
            requests += 1

        if requests:
            self._request = request # sample for unitest
            trigger.wakeup ()

        if _reqtype [-3:] == "rpc":
            return self

    def handle_request_failed (self, rs, asyncon, task = 'request'):
        self._logger ("creating {} failed".format (task), "fail")
        self._logger.trace ()
        rs.request_failed ()
        asyncon.set_active (False)

    def _avails (self):
        return len (self._nodes)

    def _get_connection (self, id = None):
        if id is None: id = self._nodes.pop ()
        else: self._nodes = []
        asyncon = self._cluster.get (id)
        self._setup (asyncon)
        return asyncon

    def _setup (self, asyncon):
        asyncon.set_timeout (self._timeout)
        if self._cv is None:
            self._cv = asyncon._cv

    def _cancel (self):
        with self._cv:
            self._canceled = True

    def _count (self):
        with self._cv:
            return len (self._requests)

    #---------------------------------------------------------
    def _fail_log (self, status):
        if self._origin:
            self._logger ("backend status is {}, {} at {} LINE {}: {}".format (
                status, self._origin [3], self._origin [1], self._origin [2], self._origin [4][0].strip ()
            ), "debug")

    def _collect (self, rs, failed = False):
        with self._cv:
            if not failed and self._canceled:
                return
            try:
                asyncon = self._requests.pop (rs)
            except KeyError:
                return

        status = rs.get_status ()
        if status == REQFAIL:
            with self._cv:
                self._results.append (rs)
            self._cluster.report (asyncon, True) # not asyncons' Fault

        elif status == TIMEOUT:
            with self._cv:
                self._results.append (rs)
            self._cluster.report (asyncon, False) # not asyncons' Fault

        elif not self._mapreduce and status == NETERR and self._retry < (self._numnodes - 1):
            self._logger ("cluster response error, switch to another...", "fail")
            self._cluster.report (asyncon, False) # exception occured
            with self._cv:
                self._retry += 1
                self._canceled = False
                self._nodes = [None]
            return self.rerequest ()

        elif status >= NETERR:
            with self._cv:
                self._results.append (rs)
            if status == NETERR:
                self._cluster.report (asyncon, False) # exception occured
            else:
                self._cluster.report (asyncon, True) # well-functioning
                rs.do_filter ()

        with self._cv:
            requests = self._requests
            callback, self._callback = self._callback, None

        if not requests:
            if callback:
                self._do_callback (callback)
            elif not failed:
                cv = self._ccv is not None and self._ccv or self._cv
                with cv:
                    cv.notify_all ()

    def _do_callback (self, callback):
        result = self.dispatch (wait = False)
        tuple_cb (result, callback)

    #-----------------------------------------------------------------
    def rerequest (self):
        self._build_request (*self._cached_request_args)

    def reset_timeout (self, timeout, ccv = None):
        with self._cv:
            self._timeout = timeout
            self._ccv = ccv
            asyncons = list (self._requests.values ())

        if timeout > 0:
            for asyncon in asyncons:
                asyncon.set_timeout (timeout)

    def set_callback (self, callback, reqid = None, timeout = None):
        if reqid is not None:
            self._meta ["__reqid"] = reqid

        if self._cv:
            with self._cv:
                requests = self._requests
                self._callback = callback
        else:
            # already finished or will use cache
            requests = self._requests
            self._callback = callback

        if not requests:
            return self._do_callback (callback)
        timeout and self.reset_timeout (timeout)

    # synchronous methods ----------------------------------------------
    def _wait (self, timeout = None):
        timeout and self.reset_timeout (timeout)
        remain = self._timeout - (time.time () - self._init_time)
        if remain > 0:
            with self._cv:
                if self._requests and not self._canceled:
                    self._cv.wait (remain)

        self._canceled = True
        requests = list (self._requests.items ())
        for rs, asyncon in requests:
            rs.set_status (TIMEOUT)
            asyncon.handle_abort () # abort imme
            self._collect (rs, failed = True)

    def dispatch (self, cache = None, cache_if = (200,), timeout = None, wait = True, reraise = False):
        if self._cached_result is not None:
            return self._cached_result
        wait and self._wait (timeout)
        rss = [rs.get_result () for rs in self._results]
        for rs in rss:
            if rs.status == NORMAL and rs.status_code < 300:
                continue
            self._fail_log (rs.status)
            reraise and rs.reraise ()

        if self._mapreduce:
            self._cached_result = Results (rss, ident = self._get_ident ())
        else:
            self._cached_result = rss [0]
        self.cache (cache, cache_if)
        return self._cached_result

    def dispatch_or_throw (self, cache = None, cache_if = (200,), timeout = None):
        return self.dispatch (cache, cache_if, reraise = True, timeout = timeout)

    def none_or_dispatch (self, cache = None, cache_if = (200,), timeout = None):
        r = self.dispatch (cache, cache_if, reraise = True, timeout = timeout)
        if r.data is not None:
          return r

    def wait (self, timeout = None, reraise = False):
        return self.dispatch (reraise = reraise, timeout = timeout)

    # direct access to data ----------------------------------------------

    def commit (self, timeout = None):
        return self.wait (timeout, True)
    wait_or_throw = commit

    def fetch (self, cache = None, cache_if = (200,), timeout = None):
        res = self._cached_result or self.dispatch (timeout = timeout, reraise = True)
        return res.fetch (cache or self._cache_timeout, cache_if)

    def one (self, cache = None, cache_if = (200,), timeout = None):
        try:
            res = self._cached_result or self.dispatch (timeout = timeout, reraise = True)
        except (PGIntegrityError, sqlite3.IntegrityError):
            raise exceptions.HTTPError ("409 Conflict")
        return res.one (cache or self._cache_timeout, cache_if)

    def then (self, func):
        from ..tasks import Future
        return Future (self, self._timeout, meta = self._meta).then (func)

    def cache (self, cache = 60, cache_if = (200,)):
        cache = cache or self._cache_timeout
        if not cache:
            return self
        if self._cached_result is None:
            raise ValueError("call dispatch first")
        self._cached_result.cache (cache, cache_if)
        return self
    getwait = getswait = dispatch # lower ver compat.
    getwait_or_throw = getswait_or_throw = dispatch_or_throw # lower ver compat.


# cluster base call ---------------------------------------
class _Method:
    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))

    def __call__(self, *args):
        return self.__send(self.__name, args)


class Proxy:
    def __init__ (self, __class, *args, **kargs):
        self.__class = __class
        self.__args = args
        self.__kargs = kargs

    def __enter__ (self):
        return self

    def __exit__ (self, type, value, tb):
        pass

    def __getattr__ (self, name):
        return _Method (self.__request, name)

    def __request (self, method, params):
        cdc = self.__class (*self.__args, **self.__kargs)
        cdc._build_request (method, params)
        return cdc


class TaskCreator:
    def __init__ (self, cluster, logger, cachesfs):
        self.cluster = cluster
        self.logger = logger
        self.cachesfs = cachesfs

    def __getattr__ (self, name):
        return getattr (self.cluster, name)

    def Server (self, uri, params = None, reqtype="rpc", headers = None, auth = None, meta = None, use_cache = True, mapreduce = False, filter = None, callback = None, cache = None, timeout = DEFAULT_TIMEOUT, caller = None):
        if type (headers) is list:
            h = {}
            for n, v in headers:
                h [n] = v
            headers = h

        if reqtype.endswith ("rpc"):
            return Proxy (Task, self.cluster, uri, params, reqtype, headers, auth, meta, use_cache, mapreduce, filter, callback, cache, timeout, caller, self.cachesfs, self.logger)
        else:
            return Task (self.cluster, uri, params, reqtype, headers, auth, meta, use_cache, mapreduce, filter, callback, cache, timeout, caller, self.cachesfs, self.logger)
