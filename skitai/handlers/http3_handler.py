from . import http2_handler
import skitai
from rs4 import producers
from .http3 import QUIC
from .http2.request import request as http2_request
from .http2.vchannel import fake_channel, data_channel
import threading
from io import BytesIO
import time
from ..backbone.lifetime import maintern
from aioquic.quic import events
from aioquic.h3 import connection as h3
from aioquic.h3.events import DataReceived, HeadersReceived, PushPromiseReceived, H3Event
from aioquic.quic.connection import stream_is_unidirectional
from aioquic.buffer import Buffer
from dataclasses import dataclass
import collections

@dataclass
class StreamEnded (H3Event):
    stream_id: int


class http3_request_handler (http2_handler.http2_request_handler):
    def __init__ (self, handler, request):
        self.handler = handler
        self.wasc = handler.wasc
        self.request = request
        self.channel = request.channel
        self.quic = None
        self.conn = None
        self.producers = collections.deque ()
        self.requests = {}
        self.promises = {}
        self._stream = {}
        self._closed = False
        self._plock = threading.Lock () # for self.conn
        self._clock = threading.Lock () # for self.x
        self._is_done = False
        self._has_sendables = False

        self._local_control_stream_id = None
        self._local_decoder_stream_id = None
        self._local_encoder_stream_id = None

        self._peer_control_stream_id = None
        self._peer_decoder_stream_id = None
        self._peer_encoder_stream_id = None

    def send_data (self):
        self._has_sendables = True

    def has_sendables (self):
        return self._has_data

    def datagrams_to_send (self):
        while self.producers:
            stream_id, headers, producer, trailers, force_close, out_bytes in self.producers [0]
            if headers:
                with self._plock:
                    self.conn.send_headers (stream_id, header, end_stream = not producer and not trailers)
                    self.producers [0][1] = None

            if producer:
                if hasattr (producer, 'ready') and not producer.ready ():
                    self.producers.rotate (-1)
                data = producer.more ()
                self.producers [0][-1] = out_bytes + len (data) # update out_bytes
            else:
                data = b''

            if not data:
                self.producers.popleft ()
                with self._plock:
                    self.conn.send_data (stream_id, b'', end_stream = True)
                r = self.get_request (stream_id)
                r.response.maybe_log (self.producers [0][-1]) # bytes
                self.remove_request (stream_id)
                if force_close:
                    return self.go_away (h3.ErrorCode.HTTP_REQUEST_CANCELLED)
                continue
            with self._plock:
                self.conn.send_data (stream_id, data, end_stream = False)
            break

        with self._plock:
            frames = [data for data, addr in self.quic.datagrams_to_send (now = time.monotonic ())]
        if not frames:
            self._has_sendables = False
        return frames

    def initiate_connection (self, data):
        self.quic = QUIC (self.channel, data, stateless_retry = False)
        self.conn = h3.H3Connection (self.quic)
        self.collect_incoming_data (data)

    def collect_incoming_data (self, data):
        with self._plock:
            self.quic.receive_datagram (data, self.channel.addr, time.monotonic ())
        self.process_quic_events ()
        self.send_data ()

    def go_away (self, errcode = h3.ErrorCode.HTTP_NO_ERROR, msg = None):
        with self._plock:
            self.quic.close (error_code=errcode, reason_phrase=msg)
        self.send_data ()
        self.channel.close_when_done ()

    def ping (self, uid):
        with self._plock:
            self.quic.send_ping (uid)
        self.send_data ()

    def process_quic_events (self):
        with self._plock:
            event = self.quic.next_event ()
        while event is not None:
            if isinstance(event, events.ConnectionIdIssued):
                pass
            elif isinstance(event, (events.ConnectionTerminated, events.ConnectionIdRetired)):
                self.close ()
            elif isinstance(event, events.HandshakeCompleted):
                pass
            elif isinstance(event, events.PingAcknowledged):
                pass
            self.handle_events (self.conn.handle_event (event))
            with self._plock:
                event = self.quic.next_event ()

    def handle_events (self, events):
        for event in events:
            if isinstance(event, HeadersReceived):
                self.handle_request (event.stream_id, event.headers)

            elif isinstance(event, DataReceived) and event.data:
                r = self.get_request (event.stream_id)
                if not r:
                    self.go_away (h3.ErrorCode.HTTP_REQUEST_CANCELLED)
                else:
                    try:
                        r.channel.set_data (event.data, event.flow_controlled_length)
                    except ValueError:
                        # from vchannel.handle_read () -> collector.collect_inconing_data ()
                        self.go_away (ErrorCodes.HTTP_REQUEST_CANCELLED)

                    if event.stream_ended:
                        if r.collector:
                            r.channel.handle_read ()
                            r.channel.found_terminator ()
                        r.set_stream_ended ()
                        if r.response.is_done ():
                            # DO NOT REMOVE before responsing
                            # this is for async streaming request like proxy request
                            self.remove_request (event.stream_id)
        self.send_data ()

    def handle_response (self, stream_id, headers, trailers, producer, do_optimize, force_close = False):
        producer and self.producers.append ([stream_id, headers, producer, trailers, force_close, 0])
        current_promises = []
        with self._clock:
            while self.promises:
                current_promises.append (self.promises.popitem ())
        for promise_stream_id, promise_headers in current_promises:
            self.handle_request (promise_stream_id, promise_headers)
        self.send_data ()


class Handler (http2_handler.Handler):
    keep_alive = 120
    def match (self, request):
        return request.version.startswith ("3.")

    def handle_request (self, request):
        http3 = http3_request_handler (self, request)
        request.channel.die_with (http3, "http3 stream")
        request.channel.set_socket_timeout (self.keep_alive)
        request.channel.current_request = http3
