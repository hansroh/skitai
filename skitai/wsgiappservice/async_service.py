import os, sys
import threading
from skitai import PROTO_SYN_HTTP, PROTO_SYN_HTTPS
from skitai import __version__, DEFAULT_BACKGROUND_TASK_TIMEOUT
from ..tasks import tasks
from ..tasks.pth import sp_task
from ..tasks.httpbase import cluster_manager, task, sync_proxy

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
    METHODS = {
        "options", "trace", "upload", "get", "delete", "post", "put", "patch",
        "rpc", "xmlrpc", "jsonrpc", "grpc", "stub",
        "ws", "wss"
    }
    DEFAULT_REQUEST_TYPE = ("application/json", "application/json")
    def __init__ (self, enable_requests = True, **options):
        enable_requests and self.make_tasks_methods ()
        self.cv = threading.Condition ()

    def make_tasks_methods (self):
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
            return self.clusters_for_distcall ["{}:{}".format (clustername, self.app.name)], "/" + uri
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
                fn = "rest"

        if fn == "map" and not hasattr (self, "threads"):
            raise AttributeError ("Cannot use Map-Reduce with Single Thread")

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
        if uri:
            uri = cluster.get_basepath () + uri
        return self._create_rest_call (cluster, uri, data, method, self.rebuild_header (headers, method, data), auth, self._set_was_id (meta), self._use_cache (use_cache, rm_cache), mapreduce, filter, callback, cache, timeout, caller)

    def _lb (self, *args, **karg):
        return self._crest (False, *args, **karg)

    def _map (self, *args, **karg):
        return self._crest (True, *args, **karg)

    # async options ------------------------------------------
    def _create_rest_call (self, cluster, *args, **kargs):
        if cluster is None or cluster.use_syn_connection or cluster.ctype in (PROTO_SYN_HTTP, PROTO_SYN_HTTPS):
            if args [2].endswith ("rpc") or args [2] == 'stub':
                return sync_proxy.ProtoCall (cluster, *args, **kargs).create_stub ()
            else:
                return sync_proxy.ProtoCall (cluster, *args, **kargs)
        else:
            return cluster.Server (*args, **kargs)

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

