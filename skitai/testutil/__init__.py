#---------------------------------------------------------------
# Skitai Unit Test Libaray
#---------------------------------------------------------------

import threading
import multiprocessing
from aquests.athreads import threadlib, trigger
import skitai
from skitai import was as the_was
from ..wastuff import triple_logger
from .. import wsgiappservice, cachefs
from ..handlers.websocket import servers as websocekts
from . import server
from ..handlers import vhost_handler
from ..handlers import proxy_handler
import inspect
import os
from ..dbi import cluster_dist_call as dcluster_dist_call
from ..rpc import cluster_dist_call
from aquests.client import socketpool
from aquests.dbapi import dbpool
from aquests import lifetime
from aquests.client import adns
from aquests.client.asynconnect import AsynConnect
from aquests.dbapi.dbconnect import DBConnect
import asyncore
from .launcher  import launch
from skitai import PROTO_HTTP, PROTO_HTTPS, PROTO_WS, DB_PGSQL, DB_SQLITE3, DB_MONGODB, DB_REDIS
from ..wastuff import semaps
     
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

def setup_was (wasc):
    def add_cluster (wasc, name, args):
        ctype, members, policy, ssl, max_conns = args
        wasc.add_cluster (ctype, name, members, ssl, policy, max_conns)
    
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
    
    websocekts.start_websocket (wasc)
    wasc.register ("websockets", websocekts.websocket_servers)
    
    add_cluster (wasc, *skitai.alias ("@example", PROTO_HTTP, "www.example.com"))
    add_cluster (wasc, *skitai.alias ("@examples", PROTO_HTTPS, "www.example.com"))
    add_cluster (wasc, *skitai.alias ("@sqlite3", DB_SQLITE3, SAMPLE_DBPATH))
    add_cluster (wasc, *skitai.alias ("@postgresql", DB_PGSQL, "user:pass@127.0.0.1/mydb"))
    add_cluster (wasc, *skitai.alias ("@mongodb", DB_MONGODB, "127.0.0.1:27017/mydb"))
    add_cluster (wasc, *skitai.alias ("@redis", DB_REDIS, "127.0.0.1:6379"))
       
    return wasc

wasc = None
def activate ():
    from ..wsgiappservice import SyncWAS
    from atila import was as atila_was
    
    class WAS (atila_was.WAS, SyncWAS):
        numthreads = 1 
        _luwatcher = semaps.TestSemaps ()
        _stwatcher = semaps.TestSemaps ()
    
    global wasc    
    if wasc is not None:
        return
    
    wasc = setup_was (WAS)
    skitai.start_was (wasc)
    
    lifetime.init (10.0, wasc.logger.get ("server"))    
    
    