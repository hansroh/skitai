import multiprocessing
from aquests.lib.athreads import threadlib
import skitai
from skitai import was as the_was
from ..wastuff import triple_logger
from .. import wsgiappservice
from ..handlers.websocket import servers as websocekts
from . import server 
    
def logger ():
    return triple_logger.Logger ("screen", None)    

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

wasc = None
def start_was ():
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
    wasc.register ("cachefs", None)    
    websocekts.start_websocket (wasc)
    wasc.register ("websockets", websocekts.websocket_servers)
    wasc.numthreads = 0
    skitai.start_was (wasc)
