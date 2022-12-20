from ..backbone import aiochat
from rs4.protocols.sock.impl import grpc
from . import websocket_handler
from skitai import was as the_was
from rs4.protocols.sock.impl.http import http_util
from rs4.protocols.sock.impl.grpc.discover import find_input
from rs4.protocols.sock.impl.grpc.producers import serialize
from rs4.misc import compressors
import time
import asyncio

class GRPCProtocol:
    def __init__ (self, request, aiochannel):
        self.request = request
        self.aiochannel = aiochannel
        self.stream_id = request.stream_id
        self.conn = self.request.protocol.conn
        self.collector = self.request.collector
        self.out_bytes = 0
        self.closed = False

        headers = self.request.response.build_reply_header ()
        self.conn.send_headers (self.stream_id, headers, end_stream = False)

    async def send (self, msg):
        sent = await self.aiochannel.send (msg, self.stream_id)
        self.out_bytes += sent

    def __aiter__ (self):
        return self

    async def __anext__ (self):
        item = await self.receive ()
        if item is None:
            raise StopAsyncIteration
        return item

    async def receive (self):
        return await self.collector.get ()

    def close (self):
        if self.closed:
            return
        self.conn.send_headers (self.stream_id, self.request.response.get_trailers (), end_stream = True)
        self.aiochannel.commit ()
        self.request.response.log (self.out_bytes)
        self.collector.close ()
        self.aiochannel.del_stream (self.stream_id)
        self.closed = True


class GRPCAsyncChannel (aiochat.aiochat):
    def __init__ (self, request, keep_alive = 60):
        super ().__init__ (request)
        self.keep_alive = keep_alive
        self.channel = request.channel
        self.protocol = self.request.protocol
        self.conn = self.protocol.conn
        self.compressor = compressors.GZipCompressor ()
        self.streams = {}

    def del_stream (self, stream_id):
        try:
            stream = self.streams.pop (stream_id)
        except KeyError:
            pass
        else:
            stream.aiochannel = None

        if not self.streams:
            self.close ()

    def close_when_done (self):
        for stream_id in list (self.streams.keys ()):
            self.del_stream (stream_id)

    def handle_close (self):
        pass

    def close (self):
        if self._closed:
            return
        self.commit ()
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

    def move_buffered_data (self):
        data, self.channel._channel.ac_in_buffer = self.channel._channel.ac_in_buffer, b''
        self.set_terminator (self.channel._channel.get_terminator ())
        if data:
            self.find_terminator (data)
        print ("~~~~~~~~~~GRPCAsyncChannel<", data, self.get_terminator (), '>~~~~~~~~~~~~~')
        self.protocol.set_channel (self)

    def handle_connect (self):
        self.move_buffered_data ()
        self.create_stream (self.request)
        del self.request

    def create_stream (self, request):
        stream = GRPCProtocol (self.request, self)
        self.streams [self.request.stream_id] = stream
        return stream

    async def send (self, msg, stream_id):
        data = serialize (msg, True, self.compressor)
        self.conn.send_data (stream_id, data, end_stream = False)
        self.commit ()
        return len (data)

    def close (self):
        if self._closed:
            return
        self.commit ()
        self.channel._channel and self.channel._channel.close ()
        self.transport.close ()
        self.protocol.channel = None
        self._closed = True


class GRPCAsyncChannelBuilder:
    def __init__ (self, handler, request):
        self.handler = handler
        self.wasc = handler.wasc
        self.request = request

    async def open (self):
        if isinstance (self.request.protocol.channel, GRPCAsyncChannel):
            return self.request.protocol.channel.create_stream (self.request)

        transport, protocol = await self.wasc.async_executor.loop.create_connection (
            lambda: GRPCAsyncChannel (self.request),
            sock = self.request.channel.conn
        )
        return protocol.streams [self.request.stream_id]


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
        ws = GRPCAsyncChannelBuilder (self, request)
        was.stream = ws
        apph (env, donot_response)
