#---------------------------------------------------------------
# Skitai Unit Test Libaray
#---------------------------------------------------------------

import threading
import multiprocessing
from aquests.lib.athreads import threadlib, trigger
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
from aquests.protocols.dns import asyndns
import asyncore

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
        
def lifetime_loop ():
    global POLL
    while POLL:
        map = dict ([(k, v) for k, v in list (asyncore.socket_map.items ()) if isinstance (v, (DBConnect, AsynConnect, asyndns.UDPClient, asyndns.TCPClient))])
        while map:
            print (map)
            lifetime.poll_fun_wrap (1.0, map)                


wasc = None
def activate ():
    global wasc
    if wasc is not None:
        return
    
    wasc = wsgiappservice.WAS
    wasc.register ("logger", logger ())
    wasc.register ("httpserver", server.Server (wasc.logger))
    wasc.register ("debug", False)
    wasc.register ("plock", multiprocessing.RLock ())
    
    wasc.register ("clusters",  {})
    wasc.register ("clusters_for_distcall",  {})
    wasc.register ("workers", 1)
    wasc.register ("cachefs", cachefs.CacheFileSystem (None, 0, 0))    
    
    websocekts.start_websocket (wasc)
    wasc.register ("websockets", websocekts.websocket_servers)    

    skitai.start_was (wasc)
    