from . import http2_handler
import threading
import time
import os
from . import http2_handler
from aioquic.quic import events
from aioquic.h3 import connection as h3
from aioquic.h3.events import DataReceived, HeadersReceived, PushPromiseReceived, H3Event
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
)
from aioquic.quic.retry import QuicRetryTokenHandler
from aioquic.quic.connection import QuicConnection

class http3_producer (http2_handler.http2_producer):
    def local_flow_control_window (self):
        return self.SIZE_BUFFER

class http3_request_handler (http2_handler.http2_request_handler):
    producer_class = http3_producer
    stateless_retry = False

    def __init__ (self, handler, request):
        self.handler = handler
        self.wasc = handler.wasc
        self.request = request
        self.channel = request.channel
        self.quic = None
        self.conn = None
        self._retry = QuicRetryTokenHandler() if self.stateless_retry else None
        self.default_varialbes ()

    def data_to_send (self):
        if self.quic is None:
            return []
        self.data_from_producers (h3.ErrorCode.HTTP_REQUEST_CANCELLED)
        with self._plock:
            frames = [data for data, addr in self.quic.datagrams_to_send (now = time.monotonic ())]
        if not frames and not self.producers:
            self._has_sendables = False
        return frames

    def make_quic (self, channel, data):
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

        assert len (data) >= 1200 and header.packet_type == PACKET_TYPE_INITIAL
        original_connection_id = None
        if self._retry is not None:
            if not header.token:
                # create a retry token
                channel.push (
                    encode_quic_retry (
                        version = header.version,
                        source_cid = os.urandom(8),
                        destination_cid = header.source_cid,
                        original_destination_cid = header.destination_cid,
                        retry_token = self._retry.create_token (channel.addr, header.destination_cid),
                    )
                )
                return

            else:
                try:
                    original_connection_id = self._retry.validate_token (
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

    def collect_incoming_data (self, data):
        if self.quic is None:
             self.quic = self.make_quic (self.channel, data)
             if self.quic is None:
                 return
             self.conn = h3.H3Connection (self.quic)

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

    def pushable (self):
        return True

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
                self.handle_request (event.stream_id, event.headers, has_data_frame = not event.stream_ended)
                r = self.get_request (event.stream_id)
                if event.stream_ended:
                    r.set_stream_ended ()

            elif isinstance(event, DataReceived) and event.data:
                r = self.get_request (event.stream_id)
                if not r:
                    self.go_away (h3.ErrorCode.HTTP_REQUEST_CANCELLED)
                else:
                    try:
                        r.channel.set_data (event.data, len (event.data))
                    except ValueError:
                        # from vchannel.handle_read () -> collector.collect_inconing_data ()
                        self.go_away (ErrorCodes.HTTP_REQUEST_CANCELLED)

                    if event.stream_ended:
                        if r.collector:
                            r.channel.handle_read ()
                            r.channel.found_terminator ()
                        r.set_stream_ended ()
                        #if r.response.is_done ():
                            # DO NOT REMOVE before responsing
                            # this is for async streaming request like proxy request
                            # self.remove_request (event.stream_id)
        self.send_data ()

    def push_promise (self, stream_id, request_headers, addtional_request_headers):
        headers = [(k.encode (), v.encode ()) for k, v in request_headers + addtional_request_headers]
        try:
            promise_stream_id = self.conn.send_push_promise (stream_id = stream_id, headers = headers)
        except NoAvailablePushIDError:
            return
        self.handle_events ([HeadersReceived (headers = headers, stream_ended = True, stream_id = promise_stream_id)])


class Handler (http2_handler.Handler):
    keep_alive = 120
    def match (self, request):
        return request.version.startswith ("3.")

    def handle_request (self, request):
        http3 = http3_request_handler (self, request)
        request.channel.die_with (http3, "http3 stream")
        request.channel.set_socket_timeout (self.keep_alive)
        request.channel.current_request = http3
