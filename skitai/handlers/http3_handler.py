from . import http2_handler
import threading
import time
import os
from aioquic.quic import events
from aioquic.h3 import connection as h3
from aioquic.h3.events import DataReceived, HeadersReceived, PushPromiseReceived, H3Event
from aioquic.quic.connection import stream_is_unidirectional
from aioquic.buffer import Buffer
from dataclasses import dataclass
import collections
from aioquic.quic.packet import (
    PACKET_TYPE_INITIAL,
    encode_quic_retry,
    encode_quic_version_negotiation,
    pull_quic_header,
)
from aioquic.quic.retry import QuicRetryTokenHandler
from aioquic.quic.connection import QuicConnection

class http3_producer:
    def __init__ (self, stream_id, headers, producer, trailers, force_close, conn, lock):
        self.stream_id = stream_id
        self.headers = headers
        self.producer = producer
        self.trailer = trailers
        self.force_close = force_close
        self.conn = conn
        self.lock = lock
        self.bytes = 0
        self.next_data = None
        self._end_stream = False

    def set_stream_ended (self):
        self._end_stream = True

    def is_stream_ended (self):
        return self._end_stream

    def produce (self):
        if self.is_stream_ended ():
            return 0
        sent = 0
        if self.headers:
            with self.lock:
                self.conn.send_headers (self.stream_id, self.headers, end_stream = not self.producer and not self.trailers)
            self.headers = None
            sent = 1

        if not self.producer:
            self.set_stream_ended ()
            return sent

        if self.next_data is not None:
            data, self.next_data = self.next_data, None
        else:
            if hasattr (self.producer, 'ready') and not self.producer.ready ():
                return sent
            data = self.producer.more ()
            if not data:
                self.set_stream_ended ()
                with self.lock:
                    self.conn.send_data (stream_id, b'', end_stream = True)
                return 1

        if not hasattr (self.producer, 'ready') or self.producer.ready ():
            self.next_data = self.producer.more ()
            if not self.next_data:
                self.set_stream_ended ()

        self.bytes += len (data)
        with self.lock:
            self.conn.send_data (self.stream_id, data, end_stream = self.is_stream_ended ())
        return 1


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

    def send_data (self):
        self._has_sendables = True

    def has_sendables (self):
        return self._has_sendables

    def data_to_send (self):
        for i in range (len (self.producers)):
            with self._clock:
                producer = self.producers [0]
            produced = producer.produce ()
            if producer.is_stream_ended ():
                with self._clock:
                    self.producers.popleft ()
                r = self.get_request (producer.stream_id)
                r.response.maybe_log (producer.bytes) # bytes
                self.remove_request (producer.stream_id)
                if producer.force_close:
                    return self.go_away (h3.ErrorCode.HTTP_REQUEST_CANCELLED)
            if produced:
                break
            with self._clock:
                self.producers.rotate (-1)
            continue

        with self._plock:
            frames = [data for data, addr in self.quic.datagrams_to_send (now = time.monotonic ())]
        if not frames and not self.producers:
            self._has_sendables = False
        return frames

    def make_quic (self, channel, data, stateless_retry = False):
        ctx = channel.server.ctx
        _retry = QuicRetryTokenHandler() if stateless_retry else None

        buf = Buffer (data=data)
        header = pull_quic_header (
            buf, host_cid_length = ctx.connection_id_length
        )
        # version negotiation
        if header.version is not None and header.version not in ctx.supported_versions:
            self.channel.push (
                encode_quic_version_negotiation (
                    source_cid = header.destination_cid,
                    destination_cid = header.source_cid,
                    supported_versions = ctx.supported_versions,
                )
            )
            return

        assert len (data) >= 1200
        assert header.packet_type == PACKET_TYPE_INITIAL
        original_connection_id = None
        if _retry is not None:
            if not header.token:
                # create a retry token
                channel.push (
                    encode_quic_retry (
                        version = header.version,
                        source_cid = os.urandom(8),
                        destination_cid = header.source_cid,
                        original_destination_cid = header.destination_cid,
                        retry_token = _retry.create_token (channel.addr, header.destination_cid),
                    )
                )
                return

            else:
                try:
                    original_connection_id = _retry.validate_token (
                        channel.addr, header.token
                    )
                except ValueError:
                    return

        # create new connection
        return QuicConnection (
            configuration = ctx,
            logger_connection_id = original_connection_id or header.destination_cid,
            original_connection_id = original_connection_id,
            session_ticket_fetcher = channel.server.ticket_store.pop,
            session_ticket_handler = channel.server.ticket_store.add
        )

    def initiate_connection (self, data):
        self.quic = self.make_quic (self.channel, data, stateless_retry = False)
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

    def push_promise (self, stream_id, request_headers, addtional_request_headers):
        headers = request_headers + addtional_request_headers
        try:
            promise_stream_id = self.conn.send_push_promise (stream_id = self.stream_id, headers = headers)
        except NoAvailablePushIDError:
            return
        self.handle_events ([HeadersReceived (headers = headers, stream_ended = True, stream_id = push_stream_id)])

    def handle_response (self, stream_id, headers, trailers, producer, do_optimize, force_close = False):
        self.producers.append (http3_producer (stream_id, headers, producer, trailers, force_close, self.conn, self._plock))


class Handler (http2_handler.Handler):
    keep_alive = 120
    def match (self, request):
        return request.version.startswith ("3.")

    def handle_request (self, request):
        http3 = http3_request_handler (self, request)
        request.channel.die_with (http3, "http3 stream")
        request.channel.set_socket_timeout (self.keep_alive)
        request.channel.current_request = http3
