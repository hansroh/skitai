from rs4.protocols.sock.impl import grpc
from . import wsgi_handler
from skitai import was as the_was
from rs4.protocols.sock.impl.http import http_util
from rs4.protocols.sock.impl.grpc.discover import find_input
from rs4.protocols.sock.impl.grpc.producers import serialize
from rs4.misc import compressors

class GRPCAsyncStream:
    STREAM_TYPE = 'grpc'
    def __init__ (self, request):
        self.request = request
        self.stream_id = request.stream_id
        self.protocol = request.protocol
        self.conn = self.protocol.conn
        self.lock = self.protocol._plock
        self.collector = self.request.collector
        self.closed = False
        self.compressor = compressors.GZipCompressor ()
        headers = self.request.response.build_reply_header ()
        with self.lock:
            self.conn.send_headers (self.stream_id, headers, end_stream = False)
        self.protocol.flush ()

    def __aiter__ (self):
        return self

    async def __anext__ (self):
        item = await self.receive ()
        if item is None:
            raise StopAsyncIteration
        return item

    async def receive (self):
        return await self.collector.get ()

    def send (self, msg):
        data = serialize (msg, True, self.compressor)
        with self.lock:
            self.conn.send_data (self.stream_id, data, end_stream = False)
        self.protocol.flush ()

    def close (self):
        if self.closed:
            return
        with self.lock:
            self.conn.send_headers (self.stream_id, self.request.response.get_trailers (), end_stream = True)
        self.protocol.flush ()
        self.collector.close ()
        self.closed = True


class Handler (wsgi_handler.Handler):
    def __init__(self, wasc, apps = None):
        self.wasc = wasc
        self.apps = apps
        self.set_default_env ()

    def match (self, request):
        return request.get_header ("content-type", "").startswith ('application/grpc')

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

        stream = GRPCAsyncStream (request)
        request.channel.die_with (stream, "grpc stream")
        was.stream = stream
        apph (env, donot_response)
