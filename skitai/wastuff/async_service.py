import os, sys
import threading
from skitai import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB, DB_SYN_PGSQL, PROTO_SYN_HTTP, PROTO_SYN_HTTPS
from ..corequest.httpbase import cluster_manager, task, sync_proxy
from ..corequest.dbi import cluster_manager as dcluster_manager, task as dtask
from sqlphile import Template
from sqlphile import pg2, db3

def is_main_thread ():
    return isinstance (threading.currentThread (), threading._MainThread)

class Command:
    def __init__ (self, name, callback):
        self.name = name
        self.callback = callback

    def __call__ (self, *args, **kargs):
        return self.callback (self.name, args, kargs)

    def lb (self, *args, **kargs):
        return self.callback (self.name + ".lb", args, kargs)

    def map (self, *args, **kargs):
        return self.callback (self.name + ".map", args, kargs)


class AsyncService:
    ASYNCDBA = {
        "asyncon", "backend", "db", "postgresql", "sqlite3", "redis", "mongodb"
    }
    METHODS = {
        "options", "trace", "upload", "get", "delete", "post", "put", "patch",
        "rpc", "xmlrpc", "jsonrpc", "grpc",
        "ws", "wss"
    }.union (ASYNCDBA)
    DEFAULT_REQUEST_TYPE = ("application/json", "application/json")
    DEFAULT_SQL_TEMPLATE_ENGINES = {
        DB_PGSQL: Template (DB_PGSQL),
        DB_SYN_PGSQL: Template (DB_SYN_PGSQL),
        DB_SQLITE3: Template (DB_SQLITE3),
    }
    def __init__ (self, enable_requests = True, **options):
        enable_requests and self.make_corequest_methods ()
        self.cv = threading.Condition ()

    def make_corequest_methods (self):
        for method in self.METHODS:
            setattr (self, method, Command (method, self._call))

    @classmethod
    def add_cluster (cls, clustertype, clustername, clusterlist, ssl = 0, access = [], max_conns = 100):
        if clustertype and clustertype [0] == "*":
            clustertype = clustertype [1:]
        ssl = 0
        if ssl in (1, True, "1", "yes") or clustertype in ("https", "wss", "grpcs", "rpcs"):
            ssl = 1
        if type (clusterlist) is str:
            clusterlist = [clusterlist]

        if clustertype and "*" + clustertype in (DB_PGSQL, DB_SYN_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB):
            cluster = dcluster_manager.ClusterManager (clustername, clusterlist, "*" + clustertype, access, max_conns, cls.logger.get ("server"))
            cls.clusters_for_distcall [clustername] = dtask.TaskCreator (cluster, cls.logger.get ("server"))
        else:
            cluster = cluster_manager.ClusterManager (clustername, clusterlist, clustertype, access, max_conns, cls.logger.get ("server"))
            cls.clusters_for_distcall [clustername] = task.TaskCreator (cluster, cls.logger.get ("server"), cls.cachefs)
        cls.clusters [clustername] = cluster

    def __detect_cluster (self, clustername):
        try:
            clustername, uri = clustername.split ("/", 1)
        except ValueError:
            clustername, uri = clustername, ""
        if clustername [0] == "@":
            clustername = clustername [1:]

        try:
            return self.clusters_for_distcall ["{}:{}".format (clustername, self.app.app_name)], "/" + uri
        except (KeyError, AttributeError):
            return self.clusters_for_distcall [clustername], "/" + uri

    def _call (self, method, args, karg):
        uri = None
        if args:
            uri = args [0]
        elif karg:
            uri = karg.get ("uri", "")
        if not uri:
            raise AssertionError ("Missing param uri or cluster name")

        try:
            command, fn = method.split (".")
        except ValueError:
            command = method
            if uri [0] == "@":
                fn = "lb"
            else:
                fn = (command in self.ASYNCDBA and "db" or "rest")

        if fn == "map" and not hasattr (self, "threads"):
            raise AttributeError ("Cannot use Map-Reduce with Single Thread")

        if command in self.ASYNCDBA:
            return getattr (self, "_a" + fn) ("*" + command, *args, **karg)
        else:
            return getattr (self, "_" + fn) (command, *args, **karg)

    def _set_was_id (self, meta):
        meta = meta or {}
        meta ['__was_id'] = self.ID
        return meta

    def _use_cache (self, use_cache, rm_cache):
        if rm_cache:
            self.setlu (rm_cache)
            return False
        if isinstance (use_cache, str):
            return self.getlu (use_cache)
        if isinstance (use_cache, (list, tuple)):
            return self.getlu (*use_cache)
        return use_cache

    def _rest (self, method, uri, data = None, auth = None, headers = None, meta = None, use_cache = True, rm_cache = None, filter = None, callback = None, cache = None, timeout = task.DEFAULT_TIMEOUT, caller = None):
        return self._create_rest_call (self.clusters_for_distcall ["__socketpool__"], uri, data, method, self.rebuild_header (headers, method, meta, False), auth, self._set_was_id (meta), self._use_cache (use_cache, rm_cache), False, filter, callback, cache, timeout, caller)

    def _crest (self, mapreduce = False, method = None, uri = None, data = None, auth = None, headers = None, meta = None, use_cache = True, rm_cache = None, filter = None, callback = None, cache = None, timeout = task.DEFAULT_TIMEOUT, caller = None):
        cluster, uri = self.__detect_cluster (uri)
        return self._create_rest_call (cluster, uri, data, method, self.rebuild_header (headers, method, data), auth, self._set_was_id (meta), self._use_cache (use_cache, rm_cache), mapreduce, filter, callback, cache, timeout, caller)

    def _lb (self, *args, **karg):
        return self._crest (False, *args, **karg)

    def _map (self, *args, **karg):
        return self._crest (True, *args, **karg)

    def _bind_sqlphile (self, dbo, dbtype):
        try:
            template_engine = self.app.get_sql_template () # Atila has
        except AttributeError:
            template_engine = None
        template_engine = template_engine or self.DEFAULT_SQL_TEMPLATE_ENGINES [dbtype]
        return template_engine.new (dbo)

    def _ddb (self, server, dbname = "", auth = None, dbtype = DB_PGSQL, meta = None, use_cache = False, rm_cache = None, filter = None, callback = None, cache = None, timeout = task.DEFAULT_TIMEOUT, caller = None):
        dbo = self._create_dbo (self.clusters_for_distcall ["__dbpool__"], server, dbname, auth, dbtype, self._set_was_id (meta), self._use_cache (use_cache, rm_cache), False, filter, callback, cache, timeout, caller)
        if dbtype in (DB_PGSQL, DB_SQLITE3, DB_SYN_PGSQL):
            return self._bind_sqlphile (dbo, dbtype)
        return dbo

    def _cddb (self, mapreduce = False, clustername = None, meta = None, use_cache = False, rm_cache = None, filter = None, callback = None, cache = None, timeout = task.DEFAULT_TIMEOUT, caller = None):
        cluster = self.__detect_cluster (clustername) [0]
        dbo = self._create_dbo (cluster, None, None, None, None, self._set_was_id (meta), self._use_cache (use_cache, rm_cache), mapreduce, filter, callback, cache, timeout, caller)
        if cluster.cluster.dbtype in (DB_PGSQL, DB_SQLITE3, DB_SYN_PGSQL):
            return self._bind_sqlphile (dbo, cluster.cluster.dbtype)
        return dbo

    def _dlb (self, *args, **karg):
        return self._cddb (False, *args, **karg)

    def _dmap (self, *args, **karg):
        return self._cddb (True, *args, **karg)

    def _adb (self, dbtype, server, dbname = "", auth = None, meta = None, use_cache = False, rm_cache = None, filter = None, callback = None, cache = None, timeout = task.DEFAULT_TIMEOUT, caller = None):
        return self._ddb (server, dbname, auth, dbtype, self._set_was_id (meta), use_cache, rm_cache, filter, callback, cache, timeout, caller)

    def _alb (self, dbtype, *args, **karg):
        return self._cddb (False, *args, **karg)

    def _amap (self, dbtype, *args, **karg):
        return self._cddb (True, *args, **karg)

    # async options ------------------------------------------
    def _create_rest_call (self, cluster, *args, **kargs):
        if cluster is None or cluster.use_syn_connection or cluster.ctype in (PROTO_SYN_HTTP, PROTO_SYN_HTTPS):
            if args [2].endswith ("rpc"):
                return sync_proxy.ProtoCall (cluster, *args, **kargs).create_stub ()
            else:
                return sync_proxy.ProtoCall (cluster, *args, **kargs)
        else:
            return cluster.Server (*args, **kargs)

    def _create_dbo (self, cluster, *args, **kargs):
        return cluster.Server (*args, **kargs)

    # special purpose synchronous connection ---------------------------------------
    def transaction (self, clustername):
        cluster = self.__detect_cluster (clustername) [0]
        return cluster.open2 ()

    def sdb (self, clustername):
        # single connection / multi cursors
        cluster = self.__detect_cluster (clustername) [0]
        return cluster.open3 ()

