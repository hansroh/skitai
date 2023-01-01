# Web Socket message dump and load related codes are based on websocket-server 0.4
# by Johan Hanssen Seferidis
# https://pypi.python.org/pypi/websocket-server
#
# 2016. 1. 16 Modified by Hans Roh

from . import wsgi_handler
from hashlib import sha1
from base64 import b64encode
from ..backbone.http_response import catch
from rs4.protocols.sock.impl.http import http_util
from skitai import version_info, was as the_was
from .websocket import specs
import skitai
import inspect

class Handler (wsgi_handler.Handler):
    def __init__(self, wasc, apps = None):
        self.wasc = wasc
        self.apps = apps
        self.set_default_env ()

    def match (self, request):
        return request.get_header ("upgrade") == 'websocket' and request.command == "get"

    def close (self):
        pass

    GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'.encode ()
    def calculate_response_key (self, key):
        hash = sha1(key.encode() + self.GUID)
        response_key = b64encode(hash.digest()).strip()
        return response_key.decode('ASCII')

    def build_response_header (self, request, protocol, securekey, host, path):
        headers = [
            ("Sec-WebSocket-Accept", self.calculate_response_key (securekey)),
            ("Upgrade", "Websocket"),
            ("Connection", "Upgrade"),
            ("WebSocket-Protocol", protocol),
            ("WebSocket-Location", "ws://" + host + path)
        ]
        for k, v in headers:
            request.response.set (k, v)

    def handle_request (self, request):
        def donot_response (self, *args, **kargs):
            def push (thing):
                raise AssertionError ("Websocket can't use start_response ()")
            return push

        host = request.get_header ("host")
        protocol = request.get_header ("sec-websocket-protocol", 'unknown')
        securekey = request.get_header ("sec-websocket-key")
        if not host or not securekey:
            return self.handle_error_before_collecting (request, 400)

        path, params, query, fragment = request.split_uri ()
        _valid, apph = self.get_apph (request, path)
        if not _valid:
            return apph

        app = apph.get_callable()
        is_atila = hasattr (app, 'ATILA_THE_HUN')
        if is_atila:
            # safari does not support Authorization
            if self.check_authentification (app, request, if_available = True):
                return

        try:
            collector_class = app.get_collector (request, self.get_path_info (request, apph))
        except AttributeError:
            pass
        else:
            if collector_class:
                collector = self.make_collector (collector_class, request, 0)
                self.build_response_header (request, protocol, securekey, host, path)
                request.collector = collector
                collector.start_collect ()

        env = self.build_environ (request, apph)
        was = the_was._get ()
        was.request = request
        was.env = env
        was.app = app

        env ["skitai.was"] = was
        env ["websocket.event"] = skitai.WS_EVT_INIT

        message_encoding = skitai.WS_MSG_DEFAULT
        if not is_atila:    # not Skitao-Atila
            apph (env, donot_response)
            wsconfig = env.get ("websocket.config", ())

            if len (wsconfig) == 3:
                design_spec_, keep_alive, varnames = wsconfig
            elif len (wsconfig) == 4:
                design_spec_, keep_alive, varnames, env ["websocket.session"] = wsconfig
            else:
                raise AssertionError ("You should config (design_spec, keep_alive, var_names) where env has key 'skitai.websocket.config'")
            if type (varnames) not in (list, tuple):
                varnames = (varnames,)

        else:
            current_app, method, kargs, options, resp_code = apph.get_callable().get_method (env ["PATH_INFO"], request)
            if resp_code:
                return request.response.error (resp_code)

            request.env = env # IMP
            env ["wsgi.routed"] = wsfunc = current_app.get_routed (method)
            env ["wsgi.route_options"] = options
            fspec = app.get_function_spec (wsfunc, options.get ('opts')) or inspect.getfullargspec (wsfunc)
            savedqs = env.get ('QUERY_STRING', '')
            current_args = {}
            defaults = 0
            if savedqs:
                current_args = http_util.crack_query (env ['QUERY_STRING'])
            if fspec.defaults:
                defaults = len (fspec.defaults)

            varnames = fspec.args [1:]
            valid_param_begin = 0 if options.get ('async_stream') else 1
            if defaults:
                required = varnames [valid_param_begin:-defaults]
            else:
                required = varnames [valid_param_begin:]

            for r in required:
                if r not in current_args:
                    return self.handle_error_before_collecting (request, 400)

            if not fspec.varkw:
                for p in current_args:
                    if p not in varnames:
                        return self.handle_error_before_collecting (request, 400)

            temporary_args = "&".join ([arg + "=" for arg in varnames [:len (varnames) - defaults] if current_args.get (arg) is None])
            if temporary_args:
                if savedqs:
                    env ['QUERY_STRING'] = savedqs + "&" + temporary_args
                else:
                    env ['QUERY_STRING'] = temporary_args

            apph (env, donot_response) # for setting websocket.config

            wsconfig = env.get ("websocket.config")
            if not wsconfig:
                raise AssertionError ("You should config (design_spec, keep_alive, [data_encoding]) where env has key 'was.wsconfig ()'")

            if not savedqs and "QUERY_STRING" in env:
                del env ["QUERY_STRING"]
            else:
                env ["QUERY_STRING"] = savedqs

            keep_alive = 60
            if len (wsconfig) == 4:
                design_spec_, keep_alive, message_encoding, env ["websocket.session"] = wsconfig
            elif len (wsconfig) == 3:
                design_spec_, keep_alive, message_encoding = wsconfig
            elif len (wsconfig) == 2:
                design_spec_, keep_alive = wsconfig
            elif len (wsconfig) == 1:
                design_spec_ = wsconfig [0]

        del env ["websocket.event"]
        del env ["websocket.config"]

        design_spec = design_spec_ & 31
        assert design_spec in (skitai.WS_STREAM, skitai.WS_SIMPLE), "design_spec  should be one of (WS_STREAM, WS_SIMPLE)"

        # skitai.WS_STREAM
        if is_atila and design_spec in (skitai.WS_STREAM,):
            request.response.set_reply ("101 Web Socket Protocol Handshake")
            request.channel.push (request.response.build_reply_header ().encode ())
            env ["wsgi.multithread"] = 0
            env ["stream.handler"] = (current_app, wsfunc)
            ws = specs.StreamWebSocket (self, request, apph, env, varnames, message_encoding)
            request.channel.set_socket_timeout (keep_alive)
            was.stream = env ["websocket"] = ws
            request.channel.die_with (ws, "websocket spec.%d" % design_spec)
            apph (env, donot_response) # call ws_executor
            return

        # skitai.WS_SIMPLE
        self.build_response_header (request, protocol, securekey, host, path)
        request.response ("101 Web Socket Protocol Handshake")
        env ["wsgi.noenv"] = False
        if design_spec_ & skitai.WS_NOPOOL == skitai.WS_NOPOOL:
            env ["wsgi.multithread"] = 0
        elif design_spec_ & skitai.WS_SESSION == skitai.WS_SESSION:
            env ["wsgi.multithread"] = 0

        varnames = varnames [:1]
        # Like AJAX, simple request of client, simple response data
        # the simplest version of stateless HTTP protocol using basic skitai thread pool
        ws_class = specs.SessionWebSocket
        if design_spec_ & skitai.WS_SEND_THREADSAFE == skitai.WS_SEND_THREADSAFE:
            ws_class = specs.SessionWebSocketSendThreadsafe
        ws = ws_class (self, request, apph, env, varnames, message_encoding)
        self.channel_config (request, ws, keep_alive)
        was.stream = env ["websocket"] = ws
        if is_atila:
            env ["stream.handler"] = (current_app, wsfunc)
        ws.open ()
        request.channel.die_with (ws, "websocket spec.%d" % design_spec)

    def channel_config (self, request, ws, keep_alive):
        request.response.done (upgrade_to =  (ws, 2))
        request.channel.set_socket_timeout (keep_alive)
