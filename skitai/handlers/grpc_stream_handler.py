from ..backbone import aiochat
from rs4.protocols.sock.impl import grpc
from . import websocket_handler
from skitai import was as the_was
from rs4.protocols.sock.impl.http import http_util
from rs4.protocols.sock.impl.grpc.discover import find_input
from rs4.protocols.sock.impl.grpc.producers import serialize
from rs4.misc import compressors
import time

class GRPCProtocol (aiochat.aiochat):
    def __init__ (self, request, keep_alive = 60):
        super ().__init__ (request)
        self.collector = self.request.collector
        self.keep_alive = keep_alive
        self.channel = request.channel
        self.protocol = self.request.protocol
        self.conn = self.protocol.conn
        self.compressor = compressors.GZipCompressor ()

    def close (self):
        if self._closed:
            return
        self.channel._channel and self.channel._channel.close ()
        self.transport.close ()
        self._closed = True

    def log_bytes_out (self, data):
        lr = len (data)
        self.channel._channel.server.bytes_out.inc (lr)
        self.channel._channel.bytes_out.inc (lr)

    def log_bytes_in (self, data):
        lr = len (data)
        self.channel._channel.server.bytes_in.inc (lr)
        self.channel._channel.bytes_in.inc (lr)

    def found_terminator (self):
        self.protocol.found_terminator()

    def collect_incoming_data (self, data):
        self.protocol.collect_incoming_data (data)

    def commit (self):
        data = self.conn.data_to_send ()
        data and self.push (data)

    def handle_connect (self):
        self.ac_in_buffer, self.channel._channel.ac_in_buffer = self.channel._channel.ac_in_buffer, b''
        self.protocol.set_channel (self)
        headers = self.request.response.build_reply_header ()
        self.conn.send_headers (self.request.stream_id, headers, end_stream = False)
        self.commit ()

    async def send (self, msg):
        data = serialize (msg, True, self.compressor)
        self.conn.send_data (self.request.stream_id, data, end_stream = False)
        self.commit ()

    def close (self):
        if self._closed:
            return
        self.conn.send_headers (self.request.stream_id, self.request.response.get_trailers (), end_stream = True)
        self.commit ()
        self.channel._channel and self.channel._channel.close ()
        self.transport.close ()
        self.protocol.channel = None
        self._closed = True


class StreamBuilder:
    def __init__ (self, handler, request):
        self.handler = handler
        self.wasc = handler.wasc
        self.request = request

    async def open (self):
        transport, protocol = await self.wasc.async_executor.loop.create_connection (
            lambda: GRPCProtocol (self.request),
            sock = self.request.channel.conn
        )
        return protocol


class Handler (websocket_handler.Handler):
    def __init__(self, wasc, apps = None):
        self.wasc = wasc
        self.apps = apps

    def build_response_header (self, request):
        request.response.set ("grpc-accept-encoding", 'identity,gzip')
        request.response.set_trailer ("grpc-status", "0")
        request.response.set_trailer ("grpc-message", "ok")

    def handle_request (self, request):
        def donot_response (self, *args, **kargs):
            def push (thing):
                raise AssertionError ("Stream can't use start_response ()")
            return push

        path, params, query, fragment = request.split_uri ()
        _valid, apph = self.get_apph (request, path)
        if not _valid:
            return apph

        app = apph.get_callable()
        collector_class = app.get_collector (request, self.get_path_info (request, apph))
        collector = self.make_collector (collector_class, request, 0)
        self.build_response_header (request)
        input_type = find_input (request.uri [1:])
        collector.set_input_type (input_type)
        request.collector = collector
        collector.start_collect ()

        env = self.build_environ (request, apph)
        was = the_was._get ()
        was.request = request
        was.env = env
        was.app = app
        env ["skitai.was"] = was

        current_app, method, kargs, options, resp_code = apph.get_callable().get_method (env ["PATH_INFO"], request)
        if resp_code:
            return request.response.error (resp_code)

        options ['grpc.input_stream'] = input_type [1]
        request.env = env # IMP
        env ["wsgi.routed"] = wsfunc = current_app.get_routed (method)
        env ["wsgi.route_options"] = options
        env ["wsgi.multithread"] = 0
        env ["stream.handler"] = (current_app, wsfunc)

        request.channel._channel.del_channel ()
        ws = StreamBuilder (self, request)
        was.stream = ws
        apph (env, donot_response)
