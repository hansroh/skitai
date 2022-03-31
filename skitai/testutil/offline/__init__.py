#---------------------------------------------------------------
# Skitai Unit Test Libaray
#---------------------------------------------------------------

import threading
import multiprocessing
from ...protocols.threaded import threadlib, trigger
import skitai
from skitai import was as the_was
from ...wastuff import triple_logger
from ... import wsgiappservice
from ...tasks import cachefs
from ...handlers.websocket import servers as websocekts
from . import server
from ...handlers import vhost_handler
from ...handlers import proxy_handler
import inspect
import os
from ...tasks.httpbase import task, cluster_manager
from ...protocols.sock import socketpool
from ...protocols import lifetime
from ...protocols.sock.impl.dns import adns
from ...protocols.sock.asynconnect import AsynConnect
from rs4 import asyncore
from skitai import PROTO_HTTP, PROTO_HTTPS, PROTO_WS
from ...wastuff import semaps
from ...tasks.pth import executors
from ...tasks.pth import coroutine_executor
import queue

def logger ():
    return triple_logger.Logger ("screen", None)

#----------------------------------------------------------
def disable_threads ():
    [the_was.queue.put (None) for each in range (the_was.numthreads)]
    the_was.queue = None
    the_was.threads = None
    the_was.numthreads = 0

def enable_threads (numthreads = 1):
    queue = threadlib.request_queue2 ()
    the_was.queue =  queue
    the_was.threads = threadlib.thread_pool (queue, numthreads, the_was.logger.get ("server"))
    the_was.numthreads = numthreads

#----------------------------------------------------------

def mount (point, target, pref = None):
    global wasc

    for h in wasc.httpserver.handlers:
        if isinstance (h, vhost_handler.Handler):
            vh = h
            break

    if isinstance (target, str):
        target = "{} = {}".format (point, target)
    else:
        target = (point,) + target
    vh.add_route ("default", target, pref)

def install_vhost_handler (apigateway = 0, apigateway_authenticate = 0):
    global wasc

    wasc.httpserver.handlers = []
    static_max_ages = {"/img": 3600}
    enable_apigateway = apigateway
    apigateway_authenticate = apigateway_authenticate
    apigateway_realm = "Pytest"
    apigateway_secret_key = "secret-pytest"

    vh = wasc.add_handler (
        1,
        vhost_handler.Handler,
        wasc.clusters,
        wasc.cachefs,
        static_max_ages,
        enable_apigateway,
        apigateway_authenticate,
        apigateway_realm,
        apigateway_secret_key
    )
    return vh

def install_proxy_handler ():
    global wasc

    wasc.httpserver.handlers = []
    h = wasc.add_handler (
        1,
        proxy_handler.Handler,
        wasc.clusters,
        wasc.cachefs,
        False
    )
    return h

#----------------------------------------------------------

SAMPLE_DBPATH = '/tmp/example.sqlite'

def setup_was (wasc, enable_async = False):
    def add_cluster (wasc, name, args):
        ctype, members, policy, ssl, max_conns = args
        wasc.add_cluster (ctype, name, members, ssl, policy, max_conns or 10)

    # was and testutil was share objects
    try:
        wasc.register ("logger", logger ())
    except AttributeError: # class has been already setup
        return wasc

    wasc.register ("httpserver", server.Server (wasc.logger))
    wasc.register ("debug", False)

    wasc.register ("clusters",  {})
    wasc.register ("clusters_for_distcall",  {"__socketpool__": None, "__dbpool__": None})
    wasc.register ("workers", 1)
    wasc.register ("cachefs", cachefs.CacheFileSystem (None, 0, 0))
    wasc.register ("executors", executors.Executors ())

    if enable_async:
        q = queue.Queue ()
        executor = coroutine_executor.CoroutineExecutor (q)
        executor.start ()
        wasc.register ("async_queue", q)
        wasc.register ("async_executor", executor)

    websocekts.start_websocket (wasc)
    wasc.register ("websockets", websocekts.websocket_servers)

    add_cluster (wasc, *skitai.alias ("@example", PROTO_HTTP, "www.example.com"))
    add_cluster (wasc, *skitai.alias ("@examples", PROTO_HTTPS, "www.example.com"))

    return wasc

wasc = None
def activate (make_sync = True, enable_async = False):
    from ...wsgiappservice import WAS
    from atila import was as atila_was

    class WAS (atila_was.WAS):
        numthreads = 1
        _luwatcher = semaps.TestSemaps ()

    global wasc
    if wasc is not None:
        return wasc

    # convert async to sync
    if make_sync:
        cluster_manager.ClusterManager.use_syn_connection = True
        socketpool.SocketPool.use_syn_connection = True

    wasc = setup_was (WAS, enable_async)
    skitai.start_was (wasc, enable_requests = True)
    wasc._luwatcher.add (skitai.dconf ["models_keys"])
    lifetime.init (10.0, wasc.logger.get ("server"))
    return wasc
