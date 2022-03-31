import sys, os
import sys
from rs4.misc import producers
from ..backbone.http_response import catch
from ..protocols.threaded import trigger
from ..protocols.sock.impl.http.http_util import *
from . import collectors
from skitai import version_info
import threading
from io import BytesIO
import skitai
from ..utility import make_pushables
from ..utility import deallocate_was
from urllib.parse import unquote

header2env = {
    'content-length'    : 'CONTENT_LENGTH',
    'content-type'      : 'CONTENT_TYPE',
    'connection'        : 'CONNECTION_TYPE'
    }

SKITAI_VERSION = ".".join (map (lambda x: str (x), version_info [:3]))

class Handler:
    GATEWAY_INTERFACE = 'CGI/1.1'
    ENV = {
            'GATEWAY_INTERFACE': 'CGI/1.1',
            'SERVER_SOFTWARE': "Skitai App Engine/%s Python/%d.%d" % ((SKITAI_VERSION,) + sys.version_info [:2]),
            'skitai.version': tuple (version_info [:3]),
            "wsgi.version": (1, 0),
            "wsgi.errors": sys.stderr,
            "wsgi.run_once": False,
            "wsgi.input": None
    }
    SERVICE_UNAVAILABLE_TIMEOUT = 10 # sec.

    def __init__(self, wasc, apps = None):
        self.wasc = wasc
        self.apps = apps
        self.__cycle = 0
        self.__static_file_translator = None
        self.ENV ["skitai.process"] = self.wasc.workers
        self.ENV ["skitai.thread"] = 0
        if hasattr (self.wasc, "threads") and self.wasc.threads:
            self.ENV ["skitai.thread"] = len (self.wasc.threads)
            self.MAX_QUEUE = self.ENV ["skitai.thread"] * 8
        self.ENV ["wsgi.multithread"] = hasattr (self.wasc, "threads") and self.wasc.threads
        self.ENV ["wsgi.url_scheme"] = hasattr (self.wasc.httpserver, "ctx") and "https" or "http"
        self.ENV ["wsgi.multiprocess"] = self.wasc.workers > 1 and os.name != "nt"
        self.ENV ['SERVER_PORT'] = str (self.wasc.httpserver.port)
        self.ENV ['SERVER_NAME'] = self.wasc.httpserver.server_name

    def match (self, request):
        return 1

    def set_static_file_translator (self, obj):
        self.__static_file_translator = obj

    def get_path_info (self, request, apph):
        path, params = request.split_uri() [:2]
        path = request.split_uri() [0]
        if params: path = path + params
        while path and path[0] == '/':
            path = path[1:]
        if '%' in path: path = unquote (path)
        return apph.get_path_info (path)

    def build_environ (self, request, apph):
        query = request.split_uri() [2]
        env = self.ENV.copy ()
        env ['REQUEST_METHOD'] = request.command.upper()
        env ['REQUEST_URI'] = request.uri
        env ['REQUEST_VERSION'] = request.version
        env ['SERVER_PROTOCOL'] = "HTTP/" + request.version
        env ['CHANNEL_CREATED'] = request.channel.creation_time
        if query: env['QUERY_STRING'] = query [1:]
        env ['REMOTE_ADDR'] = request.channel.addr [0]
        env ['REMOTE_SERVER'] = request.channel.addr [0]
        env ['SCRIPT_NAME'] = apph.route
        env ['SCRPIT_PATH'] = apph.abspath
        env ['PATH_INFO'] = self.get_path_info (request, apph)

        for header in request.header:
            key, value = header.split(":", 1)
            key = key.lower()
            value = value.strip ()
            if key in header2env and value:
                env [header2env [key]] = value
            else:
                key = 'HTTP_%s' % ("_".join (key.split ( "-"))).upper()
                if value and key not in env:
                    env [key] = value

        for k, v in list(os.environ.items ()):
            if k not in env:
                env [k] = v

        return env

    def make_collector (self, collector_class, request, max_cl, *args, **kargs):
        collector = collector_class (self, request, *args, **kargs)
        # IMP: content_length -1 mean undetermin length by http2 or http3
        if collector.content_length is None:
            if not request.version.startswith ("2."):
                del collector
                self.handle_error_before_collecting (request, 411)
                return
            else:
                collector.set_max_content_length (max_cl)

        elif collector.content_length > max_cl: #5M
            self.wasc.logger ("server", "too large request body (%d bytes)" % collector.content_length, "wran")
            del collector
            if request.get_header ("expect") == "100-continue":
                self.handle_error_before_collecting (request, 413, False) # client doesn't send data any more, I wish.
            else:
                self.handle_error_before_collecting (request, 413)    # forcely disconnect
            return

        # ok. allow form-data
        if request.get_header ("expect") == "100-continue":
            request.response.instant ("100 Continue")

        return collector

    def handle_error_before_collecting (self, request, code, force_close = True):
        if request.version != "2.0":
            if request.command in ('post', 'put', 'patch') and force_close:
                request.response.abort (code)
            else:
                request.response.error (code)
        else:
            # keep connecting on HTTP/2 as possible
            if request.command in ('post', 'put', 'patch'):
                collector = collectors.HTTP2DummyCollector (self, request, code)
                request.collector = collector
                collector.start_collect ()
            else:
                request.response.error (code)

    def get_apph (self, request, path):
        has_route = self.apps.has_route (path)
        if has_route == 0:
            return False, self.handle_error_before_collecting (request, 404)
        if has_route == 1:
            request.response ["Location"] = "%s/" % path
            return False, self.handle_error_before_collecting (request, 308)
        apph = self.apps.get_app (path)
        if apph is None:
            return False, self.handle_error_before_collecting (request, 404)
        return True, apph

    def check_authentification (self, app, request, if_available = False):
        if not app.is_allowed_origin (request, app.access_control_allow_origin):
            return self.handle_error_before_collecting (request, 403)
        if if_available and not request.get_header ("authorization"):
            return
        if not app.is_authorized (request, app.authenticate):
            return self.handle_error_before_collecting (request, 401)

    def handle_request (self, request):
        if self.ENV ["skitai.thread"]:
            self.__cycle += 1
            if self.__cycle == 100:
                # update MAX_QUEUE
                self.__cycle = 0
                self.MAX_QUEUE = max (
                    self.ENV ["skitai.thread"] * 8,
                    self.ENV ["skitai.thread"] * int (self.SERVICE_UNAVAILABLE_TIMEOUT / self.wasc.threads.get_avg_exc_times ())
                )
            if self.wasc.queue.qsize () > self.MAX_QUEUE:
                request.response ["Retry-After"] = self.SERVICE_UNAVAILABLE_TIMEOUT * 8
                return self.handle_error_before_collecting (request, 503)

        path, params, query, fragment = request.split_uri ()
        _valid, apph = self.get_apph (request, path)
        if not _valid:
            return apph

        app = self.apps.get_app (path).get_callable()
        # for rendering error template
        request.response.current_app = app
        if request.command != "options" and skitai.HAS_ATILA and isinstance (app, skitai.HAS_ATILA):
            # pass through options, because options want authentification info.
            if self.check_authentification (app, request):
                return

        if request.command in ('post', 'put', 'patch'):
            try:
                # shoud have constructor __init__ (self, handler, request, upload_max_size, file_max_size, cache_max_size)
                collector_class = app.get_collector (request, self.get_path_info (request, apph))
            except AttributeError:
                collector_class = None
            except NotImplementedError:
                # proto buf is not ready
                return self.handle_error_before_collecting (request, 501)

            ct = request.get_header ("content-type", "")
            max_size = app.config.get ("MAX_UPLOAD_SIZE", request.max_upload_size)
            args = (max_size, max_size) # last is cache_max 1M
            if collector_class is None:
                if ct.startswith ("multipart/form-data"):
                    collector_class = collectors.MultipartCollector
                else:
                    collector_class = collectors.FormCollector

            collector = self.make_collector (collector_class, request, max_size, *args)
            if collector:
                request.collector = collector
                collector.start_collect ()

        elif request.command in ('get', 'delete', 'options'):
            self.continue_request(request)

        else:
            self.handle_error_before_collecting (request, 405)

    def continue_request (self, request, data = None, respcode = None):
        if respcode: # delayed resp code on POST
            if respcode [1]:
                # force close
                return request.response.abort (respcode [0])
            return request.response.error (respcode [0])

        try:
            path, params, query, fragment = request.split_uri ()
            apph = self.apps.get_app (path)

        except:
            self.wasc.logger.trace ("server",  request.uri)
            return request.response.error (500)

        try:
            env = self.build_environ (request, apph)
            if data:
                env ["wsgi.input"] = data
            args = (env, request.response.start_response)
            request.static_file_translator = self.__static_file_translator

        except:
            self.wasc.logger.trace ("server",  request.uri)
            return request.response.error (500, why = apph.debug and sys.exc_info () or None)

        if env ["wsgi.multithread"]:
            self.wasc.queue.put (Job (request, apph, args, self.apps, self.wasc.logger))
        else:
            Job (request, apph, args, self.apps, self.wasc.logger) ()


class Job:
    # Multi-Threaded Jobs
    def __init__(self, request, apph, args, apps, logger):
        self.request = request
        self.apps = apps
        self.apph = apph
        self.args = args
        self.logger = logger

    def __repr__(self):
        return "<Job %s %s HTTP/%s>" % (self.request.command.upper (), self.request.uri, self.request.version)

    def __str__ (self):
        return "%s %s HTTP/%s" % (self.request.command.upper (), self.request.uri, self.request.version)

    def exec_app (self):
        # this is not just for atila,
        # Task need request and response
        was = skitai.was._get ()
        was.request = self.request
        if was.request.channel is None:
            return was.log ('connection lost', 'warn', 'server')

        was.apps = self.apps
        was.response = self.request.response
        was.env = self.args [0]
        was.env ["skitai.was"] = was

        response = self.request.response
        try:
            content = self.apph (*self.args)
            will_be_push = make_pushables (response, content)
        except MemoryError:
            raise
        except:
            was.traceback ()
            trigger.wakeup (lambda p = response, d=self.apph.debug and sys.exc_info () or None: (p.error (500, "Internal Server Error", d), p.done ()) )
        else:
            if will_be_push is None: # not responsible or futures
                return

            range_ = len (will_be_push) == 1 and response.get_header ('content-length') and response.reply_code == 200 and self.request.get_header ('range')
            for part in will_be_push:
                if range_:
                    part_length = len (part)
                    try:
                        rg_start, rg_end = parse_range (range_, part_length)
                    except:
                        trigger.wakeup (lambda p = response, d=self.apph.debug and sys.exc_info () or None: (p.error (416, "Range Not Satisfiable", d), p.done ()) )
                        return
                    part = part [rg_start : rg_end + 1]
                    response.set_reply ("206 Partial Content")
                    response.update ('Content-Range', 'bytes {}-{}/{}'.format (rg_start, rg_end, part_length))
                    response.update ("Content-Length", (rg_end - rg_start) + 1)
                response.push (part)
            trigger.wakeup (lambda p = response: (p.done (),))

    def __call__(self):
        try:
            try:
                self.exec_app ()
            finally:
                self.deallocate ()
        except:
            # no response, alredy done. just log
            self.logger.trace ("server", self.request.uri)

    def deallocate (self):
        env = self.args [0]
        was = env.get ("skitai.was")
        if was is not None:
            deallocate_was (was)
