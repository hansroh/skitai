from . import http2_handler
import threading
import time
import os
from . import http2_handler
from aioquic.quic import events
from aioquic.h3 import connection as h3
from aioquic.h3.events import DataReceived, HeadersReceived, H3Event
try:
    from aioquic.h3.events import PushCanceled, ConnectionShutdownInitiated
except:
    from dataclasses import dataclass
    @dataclass
    class PushCanceled (H3Event):
        push_id: int

    @dataclass
    class ConnectionShutdownInitiated (H3Event):
        stream_id: int

from aioquic.h3.exceptions import H3Error, NoAvailablePushIDError
from aioquic.quic.connection import stream_is_unidirectional
from aioquic.buffer import Buffer
from dataclasses import dataclass
import collections
from aioquic.quic.packet import (
    PACKET_TYPE_INITIAL,
    encode_quic_retry,
    encode_quic_version_negotiation,
    pull_quic_header,
    QuicErrorCode
)
from aioquic.quic.retry import QuicRetryTokenHandler
from aioquic.quic.connection import QuicConnection

class http3_producer (http2_handler.http2_producer):
    def local_flow_control_window (self):
        return self.SIZE_BUFFER

class http3_request_handler (http2_handler.http2_request_handler):
    producer_class = http3_producer
    stateless_retry = False
    conns = {}
    def __init__ (self, handler, request):
        self.handler = handler
        self.wasc = handler.wasc
        self.request = request
        self.channel = request.channel
        self.quic = None # QUIC protocol
        self.conn = None # HTTP3 Protocol
        self._pushes = {}
        self._close_pending = False
        self._retry = QuicRetryTokenHandler() if self.stateless_retry else None
        self.default_varialbes ()

    def make_connection (self, channel, data):
        ctx = channel.server.ctx

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

        conn = self.conns.get (header.destination_cid)
        if conn:
            conn._linked_channel.close ()
            conn._linked_channel = channel
            self.quic = conn._quic
            self.conn = conn
            return

        if header.packet_type != PACKET_TYPE_INITIAL or len (data) < 1200:
            return

        original_connection_id = None
        if self._retry is not None:
            if not header.token:
                # create a retry token
                channel.push (
                    encode_quic_retry (
                        version = header.version,
                        source_cid = os.urandom (8),
                        destination_cid = header.source_cid,
                        original_destination_cid = header.destination_cid,
                        retry_token = self._retry.create_token (channel.addr, header.destination_cid)))
                return
            else:
                try:
                    original_connection_id = self._retry.validate_token (channel.addr, header.token)
                except ValueError:
                    return

        self.quic = QuicConnection (
            configuration = ctx,
            logger_connection_id = original_connection_id or header.destination_cid,
            original_connection_id = original_connection_id,
            session_ticket_fetcher = channel.server.ticket_store.pop,
            session_ticket_handler = channel.server.ticket_store.add
        )
        self.conn = h3.H3Connection (self.quic)
        self.conn._linked_channel = channel

    def collect_incoming_data (self, data):
        # print ('collect_incoming_data', self.quic, len (data))
        if self.quic is None:
             self.make_connection (self.channel, data)
             if self.quic is None:
                 return
        with self._plock:
            self.quic.receive_datagram (data, self.channel.addr, time.monotonic ())
        self.process_quic_events ()
        self.send_data ()

    def remove_request (self, stream_id):
        with self._clock:
            try:
                self._pushes.pop (stream_id)
            except KeyError:
                pass
        super ().remove_request (stream_id)

    def remove_stream (self, push_id):
        with self._clock:
            try:
                stream_id = self._pushes.pop (push_id)
            except KeyError:
                return
        super ().remove_stream (push_id)

    def reset_stream (self, stream_id):
        raise AttributeError ('HTTP/3 dose not support reset_stream')

    def cancel_push (self, push_id):
        with self._clock:
            try:
                steram_id = self._pushes.pop (push_id)
            except KeyError:
                return # already done or canceled
        if stream_id:
            with self._plock:
                if hasattr (self.conn, 'send_cancel_push'):
                    self.conn.send_cancel_push (stream_id)
            self.remove_stream (stream_id)
            self.send_data ()

    def data_to_send (self):
        if self.quic is None or self._closed:
            return []
        self.data_from_producers (h3.ErrorCode.HTTP_REQUEST_CANCELLED)
        with self._plock:
            data_to_send = [data for data, addr in self.quic.datagrams_to_send (now = time.monotonic ())]
        return data_to_send or self.data_exhausted ()

    def terminate_connection (self, with_quic = True):
        if with_quic and self.quic:
            self.quic.close ()
            self.send_data ()
        super ().terminate_connection ()

    def initiate_shutdown (self, errcode = 0, msg = ''):
        if hasattr (self.conn, 'close_connection'):
            with self._plock:
                self.conn.close_connection ()

    def pushable (self):
        return True

    def process_quic_events (self):
        with self._plock:
            event = self.quic.next_event ()
        while event is not None:
            # print (event.__class__.__name__)
            if isinstance(event, events.ConnectionIdIssued):
                self.conns [event.connection_id] = self.conn

            elif isinstance(event, events.ConnectionIdRetired):
                assert self.conns [event.connection_id] == self.conn
                conn = self.conns.pop (event.connection_id)
                conn._linked_channel = None

            elif isinstance(event, events.ConnectionTerminated):
                for cid, conn in list (self.conns.items()):
                    if conn == self.conn:
                        conn._linked_channel = None
                        del self.conns [cid]
                self.terminate_connection (with_quic = False)

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
                self.handle_request (event.stream_id, event.headers, has_data_frame = not event.stream_ended)
                r = self.get_request (event.stream_id)
                if event.stream_ended:
                    r.set_stream_ended ()

            elif isinstance(event, DataReceived) and event.data:
                r = self.get_request (event.stream_id)
                if not r:
                    self.close (QuicErrorCode.INTERNAL_ERROR)
                else:
                    try:
                        r.channel.set_data (event.data, len (event.data))
                    except ValueError:
                        self.close (QuicErrorCode.INTERNAL_ERROR)

                    if event.stream_ended:
                        if r.collector:
                            r.channel.handle_read ()
                            r.channel.found_terminator ()
                        r.set_stream_ended ()
                        if r.response.is_done ():
                            self.remove_request (event.stream_id)

            elif isinstance(event, ConnectionShutdownInitiated):
                pass

            elif isinstance(event, PushCanceled):
                self.remove_stream (event.push_id)

        self.send_data ()

    def push_promise (self, stream_id, request_headers, addtional_request_headers):
        headers = [(k.encode (), v.encode ()) for k, v in request_headers + addtional_request_headers]
        try:
            promise_stream_id = self.conn.send_push_promise (stream_id = stream_id, headers = headers)
            push_id = self.conn.get_latest_push_id ()
        except NoAvailablePushIDError:
            return
        with self._clock:
            self._pushes [push_id] = promise_stream_id
        self.handle_events ([HeadersReceived (headers = headers, stream_ended = True, stream_id = promise_stream_id, push_id = push_id)])


class Handler (http2_handler.Handler):
    # keep_alive = 37 same as http2
    # chrome QUIC timout is 30s but first time it extends more 30s only one time
    def match (self, request):
        return request.version.startswith ("3.")

    def handle_request (self, request):
        http3 = http3_request_handler (self, request)
        request.channel.die_with (http3, "http3 connection")
        request.channel.set_socket_timeout (self.keep_alive)
        request.channel.current_request = http3
