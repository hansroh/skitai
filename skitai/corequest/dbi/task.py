import time
from aquests.athreads import socket_map
from aquests.athreads import trigger
import threading
from ..httpbase import task, rcache
from rs4.attrdict import AttrDict
from aquests.dbapi import request
from rs4 import asyncore
from skitai import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB
from skitai import REQFAIL, UNSENT, TIMEOUT, NETERR, NORMAL
from rs4.cbutil import tuple_cb

class OperationTimeout (Exception):
    pass

class RequestFailed (Exception):
    pass

class FailedRequest:
    def __init__ (self, expt):
        self.description = None
        self.data = None
        self.expt = expt

        self.code, self.msg = 500, str (expt)
        self.status_code, self.reason = self.code, self.msg

    def raise_for_status (self):
        if self.expt:
            raise self.expt
    reraise = raise_for_status


class Dispatcher (task.Dispatcher):
    def __init__ (self, cv, id, ident = None, filterfunc = None, callback = None):
        self._cv = cv
        self.id = id
        self.ident = ident
        self.filterfunc = filterfunc
        self.callback = callback
        self.creation_time = time.time ()
        self.status = UNSENT
        self.result = None

    def get_result (self):
        if not self.result:
            status = self.get_status ()
            if status == REQFAIL:
                self.result = task.Result (self.id, REQFAIL, FailedRequest (RequestFailed ("Request Failed")), self.ident)
            else:
                self.result = task.Result (self.id, TIMEOUT, FailedRequest (OperationTimeout ("Operation Timeout")), self.ident)
        return self.result

    def handle_result (self, request):
        if self.get_status () == TIMEOUT:
            # timeout, ignore
            return
        status = NORMAL
        if request.expt:
            reason = str (request.expt)
            if reason == "Operation Timeout":
                status = TIMEOUT
            elif reason == "Socket Panic":
                status = NETERR
        result = task.Result (self.id, status, request, self.ident)
        self.set_status (status, result)
        tuple_cb (self, self.callback)


#-----------------------------------------------------------
# Cluster Base Call
#-----------------------------------------------------------

class Task (task.Task):
    def __init__ (
            self,
            cluster,
            server,
            dbname,
            auth,
            dbtype,
            meta = None,
            use_cache = False,
            mapreduce = True,
            filter = None,
            callback = None,
            cache = None,
            timeout = 10,
            origin = None,
            logger = None
        ):

        self._server = server
        self._dbname = dbname
        self._auth = auth
        self._dbtype = dbtype
        if self._dbtype == DB_PGSQL:
            if self._dbname in (DB_SQLITE3, DB_REDIS):
                self._dbtype = self._dbname
                self._dbname = ""
            elif self._auth in (DB_MONGODB,):
                self._dbtype = self._auth
                self._auth = None
        self.set_defaults (cluster, meta, use_cache, mapreduce, filter, callback, cache, timeout, origin, logger)

    def _get_ident (self):
        cluster_name = self._cluster.get_name ()
        if cluster_name == "__dbpool__":
            _id = "%s/%s/%s" % (self._server, self._dbname, self._auth)
        else:
            _id = cluster_name
        _id += "/%s%s" % (
            ",".join (map (lambda x: str (x), self._cached_request_args)),
            self._mapreduce and "/M" or ""
            )
        return _id

    def _get_connection (self, id = None):
        if id is None: id = self._nodes.pop ()
        else: self._nodes = []

        if self._server:
            asyncon = self._cluster.get (self._server, self._dbname, self._auth, self._dbtype)
        else:
            asyncon = self._cluster.get (id)
        self._setup (asyncon)
        return asyncon

    def _build_request (self, method, params):
        # For Django QuerySet and SQLGen
        if hasattr (params [0], "query"):
            params = (str (params [0].query),) + params [1:]

        self._cached_request_args = (method, params) # backup for retry
        if self._use_cache and rcache.the_rcache:
            self._cached_result = rcache.the_rcache.get (self._get_ident (), self._use_cache)
            if self._cached_result is not None:
                self._cached_result.meta = self._meta
                self._callback and tuple_cb (self._cached_result, self._callback)
                return

        while self._avails ():
            asyncon = self._get_connection (None)
            rs = Dispatcher (
                self._cv, asyncon.address,
                ident = not self._mapreduce and self._get_ident () or None,
                filterfunc = self._filter,
                callback = self._collect
            )
            self._requests [rs] = asyncon
            req = request.Request (
                self._dbtype,
                self._server,
                self._dbname,
                self._auth,
                method, params,
                rs.handle_result,
                self._meta
            )

            # IMP: must modify, dbconn.ConnectProxy
            try:
                asyncon.execute (req, rs, self.handle_request_failed)
            except:
                self.handle_request_failed (rs, asyncon)
                continue

        self._request = req # sample for unitest
        trigger.wakeup ()
        return self


class Proxy:
    def __init__ (self, __class, cluster, *args, **kargs):
        self.__class = __class
        self.__cluster = cluster
        self.__args = args
        self.__kargs = kargs

    @property
    def dbtype (self):
        try:
            return self.__cluster.dbtype
        except AttributError:
            return self.__args [3]

    def __enter__ (self):
        return self

    def __exit__ (self, type, value, tb):
        pass

    def __getattr__ (self, name):
        self._method = name
        return self.__proceed

    def __proceed (self, *params):
        cdc = self.__class (self.__cluster, *self.__args, **self.__kargs)
        cdc._build_request (self._method, params)
        return cdc


class TaskCreator:
    def __init__ (self, cluster, logger):
        self.cluster = cluster
        self.logger = logger

    def __getattr__ (self, name):
        return getattr (self.cluster, name)

    def Server (self, server = None, dbname = None, auth = None, dbtype = None, meta = None, use_cache = True, mapreduce = False, filter = None, callback = None, cache = None, timeout = 10, caller = None):
        return Proxy (Task, self.cluster, server, dbname, auth, dbtype, meta, use_cache, mapreduce, filter, callback, cache, timeout, caller, self.logger)
