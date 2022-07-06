#-------------------------------------------------------
# Basic Blade Server Architecture R2
# Hans Roh (hansroh@gmail.com)
# 2014.4.24 Python 2.7 port (from 2.4)
#-------------------------------------------------------

HTTPS = True
import sys, os, threading
from .backbone import http_server
from skitai import lifetime
from warnings import warn
from .backbone import https_server
from skitai import start_was
from rs4.protocols.fifo import await_fifo
from rs4.protocols.sock import asynconnect
from rs4.protocols.sock import socketpool
from .backbone.threaded import threadlib, trigger
from rs4.protocols.sock.impl.dns import adns, dns
from rs4.protocols.sock.impl.http import request_handler
from rs4.protocols.sock.impl import http2
from rs4.psutil import kill
from .handlers import vhost_handler, forward_handler
import signal
from . import wsgiappservice
from .backbone import http_response
from .handlers.websocket import servers as websocekts
from .wastuff import selective_logger, triple_logger
if os.name == "nt":
    from rs4.psutil import schedule # cron like scheduler

class Loader:
    def __init__ (self, config = None, logpath = None, varpath = None, wasc = None, debug = 0):
        self.config = config
        self.instance_name = os.path.split (config)[-1][:-5]
        self.logpath = logpath
        self.varpath = varpath
        self.debug = debug
        self.virtual_host = None
        self.num_worker = 1
        self.wasc = wasc or wsgiappservice.WAS
        self.ssl = False
        self.ctx = None
        self._exit_code = None
        self._async_enabled = False
        self.wasc_kargs = {}
        self._fifo_switched = False
        self.config_logger (self.logpath)
        self.WAS_initialize ()
        self.configure ()
        self.WAS_finalize ()

    def configure (self):
        raise SystemExit("configure must be overided")

    def set_num_worker (self, num):
        if os.name == "nt":
            num = 1
        self.num_worker = num
        self.wasc.workers = num
        os.environ ["SKITAI_WORKERS"] = str (num)

    def WAS_initialize (self):
        self.wasc.log_base_path = self.logpath
        self.wasc.var_base_path = self.varpath
        self.wasc.register ("debug", self.debug)
        self.wasc.register ("clusters",  {})
        self.wasc.register ("clusters_for_distcall",  {})
        self.wasc.register ("workers", 1)
        websocekts.start_websocket (self.wasc)
        self.wasc.register ("websockets", websocekts.websocket_servers)
        self.switch_to_await_fifo ()

    def set_model_keys (self, keys):
        self.wasc._luwatcher.add (keys)

    def get_app_by_name (self, name):
        return self.get_apps ().get (name)

    def get_apps (self):
        apps = {}
        for h in self.wasc.httpserver.handlers:
            if isinstance (h, vhost_handler.Handler):
                for vhost in h.sites.values ():
                    for name in vhost.apps.modnames:
                        apps [name] = vhost.apps.modnames [name].get_callable ()
        return apps

    def app_cycle (self, func):
        for h in self.wasc.httpserver.handlers:
            if isinstance (h, vhost_handler.Handler):
                for vhost in h.sites.values ():
                    for apphs in vhost.apps.modules.values ():
                        for apph in apphs:
                            try:
                                getattr (apph, func) ()
                            except:
                                self.wasc.logger.trace ("server")

    def WAS_finalize (self):
        global the_was

        self.wasc.register ("lifetime", lifetime)
        # internal connection should be http 1.1
        # because http2 single connection feature is useless on accessing internal resources
        # BUT we will use http2 when gRPC call, with just 1 stream per connection for speeding
        http2.MAX_HTTP2_CONCURRENT_STREAMS = 1
        request_handler.RequestHandler.FORCE_HTTP_11 = True
        start_was (self.wasc, **self.wasc_kargs)

    def config_wasc (self, **kargs):
        self.wasc_kargs = kargs

    def config_executors (self, workers, zombie_timeout, process_start = None, enable_async = 0):
        from .tasks import executors

        if process_start:
            from multiprocessing import set_start_method
            try: set_start_method (process_start, force = True)
            except RuntimeError: pass
        _executors = executors.Executors (workers, zombie_timeout, self.wasc.logger.get ("server"))
        self.wasc.register ("executors", _executors)
        self.wasc.register ("thread_executor", _executors.get_tpool ())
        self.wasc.register ("process_executor", _executors.get_ppool ())

        if enable_async:
            self._async_enabled = True
            async_executor = executors.AsyncExecutor (enable_async)
            async_executor.start ()
            self.wasc.register ("async_executor", async_executor)

    def switch_to_await_fifo (self):
        if self._fifo_switched: return
        asynconnect.AsynConnect.fifo_class = await_fifo
        asynconnect.AsynSSLConnect.fifo_class = await_fifo
        http_server.http_channel.fifo_class = await_fifo
        https_server.https_channel.fifo_class = await_fifo
        self._fifo_switched = True

    def config_certification (self, certfile, keyfile = None, pass_phrase = None):
        if not HTTPS:
            return
        self.ctx = https_server.init_context (certfile, keyfile, pass_phrase)
        self.ssl = True

    def config_forward_server (self, ip = "", port = 80, forward_to = 443):
        forward_server = http_server.http_server (ip or "", port, self.wasc.logger.get ("server"), self.wasc.logger.get ("request"))
        forward_server.zombie_timeout = 2
        forward_server.install_handler (forward_handler.Handler (self.wasc, forward_to))
        self.wasc.register ("forwardserver", forward_server)

    def config_webserver (self, port, ip = "", name = "", ssl = False, keep_alive = 10, network_timeout = 60, single_domain = None, thunks = [], quic = None, backlog = 100, multi_threaded = False, max_upload_size = 256000000, start = True):
        # maybe be configured    at first.
        if ssl and not HTTPS:
            raise SystemError("Can't start SSL Web Server")

        if not name:
            name = self.instance_name
        http_server.configure (name, network_timeout, keep_alive, multi_threaded, max_upload_size)

        if ssl and self.ctx is None:
            raise ValueError("SSL ctx not setup")
        if ssl:
            server_class = https_server.https_server
        else:
            server_class = http_server.http_server

        if self.ssl:
            httpserver = server_class (ip or "", port, self.ctx, quic, self.wasc.logger.get ("server"), self.wasc.logger.get ("request"))
        else:
            httpserver = server_class (ip or "", port, self.wasc.logger.get ("server"), self.wasc.logger.get ("request"))
        single_domain and httpserver.set_single_domain (single_domain)
        self.wasc.register ("httpserver", httpserver)
        # starting jobs before forking
        for thunk in thunks:
            thunk ()

        if start:
            self.wasc.httpserver.serve (hasattr (self.wasc, "forwardserver") and self.wasc.forwardserver or None, backlog)
            self.fork ()

    def fork (self):
        #fork here
        _exit_code = self.wasc.httpserver.fork (self.num_worker)
        if _exit_code is not None:
            self.handle_exit_code (_exit_code)

    def handle_exit_code (self, _exit_code):
        self._exit_code = _exit_code
        try:
            os.wait ()
        except OSError:
            pass

    def get_exit_code (self):
        return self._exit_code

    def config_scheduler (self, conffile):
        if os.name == "nt":
            scheduler = schedule.Scheduler (self.wasc, conffile, self.wasc.logger.get ("server"))
            self.wasc.register ("scheduler", scheduler)

    def config_logger (self, path, media = None, log_off = [], file_loggings = None):
        if not media:
            if path is not None:
                media = ["file"]
            else:
                media = ["screen"]

        http_response.http_response.log_or_not = selective_logger.SelectiveLogger (log_off)
        self.wasc.register ("logger", triple_logger.Logger (media, path, file_loggings))

        if os.name != "nt" and path:
            def hUSR1 (signum, frame):
                self.wasc.logger.rotate ()
            signal.signal(signal.SIGUSR1, hUSR1)

    def config_threads (self, numthreads = 0):
        if numthreads > 0:
            trigger.start_trigger (self.wasc.logger.get ("server"))
            queue = threadlib.request_queue2 ()
            tpool = threadlib.thread_pool (queue, numthreads, self.wasc.logger.get ("server"))
            self.wasc.register ("queue",  queue)
            self.wasc.register ("threads", tpool)
            self.wasc.numthreads = numthreads

    def install_handler_with_tuple (self, routes):
        if type (routes) is list:
            routes = {'default': routes}
        sroutes = []
        for domain in sorted (routes.keys ()): # must sort for lueatcher reservation
            sroutes.append ("@%s" % domain)
            for route, entity, pref, name in routes [domain]:
                appname = None
                if hasattr (entity, '__app__'):
                    sroutes.append ((route, entity, pref, name))
                    continue
                if type (entity) is tuple:
                    entity, appname = entity
                if not isinstance (entity, str): # app
                    sroutes.append ((route, (entity, appname), pref, name))
                    continue
                if entity.endswith (".py") or entity.endswith (".pyc"):
                    entity = os.path.join (os.getcwd (), entity) [:-3]
                    if entity [-1] == ".":
                        entity = entity [:-1]
                sroutes.append (("%s=%s%s" % (route, entity, appname and ":" + appname or ""), pref, name))
        return sroutes

    def install_handler (self,
            routes = [],
            static_max_ages = None,
            media_url = None,
            media_path = None
        ):

        self.virtual_host = self.wasc.add_handler (
            1, vhost_handler.Handler,
            static_max_ages
        )
        routes and self.update_routes (routes, media_url, media_path)

    def update_routes (self, routes, media_url = None, media_path = None):
        if self.virtual_host is None:
            return

        if type (routes) is dict:
            routes = self.install_handler_with_tuple (routes)
        else:
            if type (routes) is not list:
                routes = [routes]
            if type (routes [0]) is tuple:
                routes = self.install_handler_with_tuple (routes)

        current_rule = "default"
        for line in routes:
            config = None
            if type (line) is tuple and len (line) == 4:
                route, module, pref, name = line
                if media_url:
                    try:
                        pref.config.MEDIA_URL, pref.config.MEDIA_ROOT = media_url, media_path
                    except AttributeError:
                        pass
                self.virtual_host.add_route (current_rule, (route, module, ''), pref, name)
                continue

            if type (line) is tuple:
                line, pref, name = line

            line = line.strip ()
            if line.startswith (";") or line.startswith ("#"):
                continue
            elif line.startswith ("/"):
                if media_url:
                    try:
                        pref.config.MEDIA_URL, pref.config.MEDIA_ROOT = media_url, media_path
                    except AttributeError:
                        pass
                rtype = self.virtual_host.add_route (current_rule, line, pref, name)
            elif line:
                if line [0] == "@":
                    line = line [1:].strip ()
                current_rule = line

    def just_before_run (self, mountables = None):
        # just before run
        mountables and self.update_routes (mountables)
        self.app_cycle ('before_mount')
        self.app_cycle ('mounted')

    def run (self, timeout = 30):
        if self._exit_code is not None:
            self.close ()
            return self._exit_code # win43 master process

        try:
            try:
                if "---memtrack" in sys.argv:
                    self.wasc.logger ("server", "memory tracking enabled", "debug")
                    lifetime.enable_memory_track ()
                if "---profile" in sys.argv:
                    import cProfile
                    self.wasc.logger ("server", "profiling enabled", "debug")
                    cProfile.runctx ("lifetime.loop (timeout)", globals (), locals (), "profile.out")
                else:
                    lifetime.loop (timeout)
            except:
                self.wasc.logger.trace ("server")
        finally:
            self.close ()

        return None # worker process

    def close (self):
        self.app_cycle ('before_umount')
        self.wasc.cleanup (phase = 1)
        self.app_cycle ('umounted')
        self.wasc.cleanup (phase = 2)

        if os.name == "nt" or self.wasc.httpserver.worker_ident == "master":
            self.wasc.logger ("server", "[info] cleanup done, closing logger... bye")
            try:
                self.wasc.logger.close ()
                del self.wasc.logger
            except:
                pass

        # finally, kill child processes
        kill.child_processes_gracefully ()
