#---------------------------------------------------------------
# Skitai Unit Test Libaray
#---------------------------------------------------------------

from ...backbone.threaded import threadlib
import skitai
from ...wastuff import triple_logger
from ...handlers.websocket import servers as websocekts
from . import server
from ...handlers import vhost_handler
from rs4.protocols import lifetime
from ...wastuff import semaps
from ...tasks import executors

def logger ():
    return triple_logger.Logger ("screen", None)

#----------------------------------------------------------
def disable_threads ():
    [ skitai.was.queue.put (None) for each in range (skitai.was.numthreads) ]
    skitai.was.queue = None
    skitai.was.threads = None
    skitai.was.numthreads = 0

def enable_threads (numthreads = 1):
    queue = threadlib.request_queue2 ()
    skitai.was.queue =  queue
    skitai.was.threads = threadlib.thread_pool (queue, numthreads, skitai.was.logger.get ("server"))
    skitai.was.numthreads = numthreads

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
        static_max_ages
    )
    return vh


#----------------------------------------------------------

SAMPLE_DBPATH = '/tmp/example.sqlite'

def setup_was (wasc, enable_async = False):
    # was and testutil was share objects
    try:
        wasc.register ("logger", logger ())
    except AttributeError: # class has been already setup
        return wasc

    wasc.register ("httpserver", server.Server (wasc.logger))
    wasc.register ("debug", False)

    wasc.register ("workers", 1)

    _executors = executors.Executors ()
    wasc.register ("executors", _executors)
    wasc.register ("thread_executor", _executors.get_tpool ())
    wasc.register ("process_executor", _executors.get_ppool ())

    if enable_async:
        import asyncio
        async_executor = executors.AsyncExecutor (100)
        async_executor.start ()
        wasc.register ("async_executor", async_executor)

    websocekts.start_websocket (wasc)
    wasc.register ("websockets", websocekts.websocket_servers)

    return wasc

wasc = None
def activate (enable_async = False):
    from ...wsgiappservice import WAS
    from atila import was as atila_was
    from skitai.tasks import utils

    class WAS (atila_was.WAS):
        numthreads = 1
        _luwatcher = semaps.TestSemaps ()

    global wasc
    if wasc is not None:
        return wasc

    wasc = setup_was (WAS, enable_async)
    skitai.was = skitai._WASPool ()
    skitai.WASC = wasc

    skitai.start_was (wasc, enable_requests = True)
    utils.WAS_FACTORY = skitai.was # refresh
    wasc._luwatcher.add (skitai.dconf ["models_keys"])
    lifetime.init (10.0, wasc.logger.get ("server"))
    return wasc
