from . import http2_handler
import time
import os
from aioquic.quic import events
from aioquic.h3 import connection as h3
from aioquic.h3.events import DataReceived, HeadersReceived, H3Event
from aioquic.h3.exceptions import H3Error, NoAvailablePushIDError
from aioquic.buffer import Buffer
from aioquic.quic.packet import (
    PACKET_TYPE_INITIAL,
    encode_quic_retry,
    encode_quic_version_negotiation,
    pull_quic_header
)
from aioquic.quic.retry import QuicRetryTokenHandler
from aioquic.quic.connection import QuicConnection
import enum
try:
    from aioquic.h3.events import PushCanceled
except:
    from dataclasses import dataclass
    @dataclass
    class PushCanceled (H3Event):
        push_id: int

# http2 compat error codes
class ErrorCode (enum.IntEnum):
    NO_ERROR = 0x0
    PROTOCOL_ERROR = 0xA
    INTERNAL_ERROR = 0x1
    FLOW_CONTROL_ERROR = 0x3
    CANCEL = 0x0

class http3_producer (http2_handler.http2_producer):
    def local_flow_control_window (self):
        return self.SIZE_BUFFER

class http3_request_handler (http2_handler.http2_request_handler):
    producer_class = http3_producer
    stateless_retry = False
    conns = {}
    errno = ErrorCode

    def __init__ (self, handler, request):
        self.default_varialbes (handler, request)

        self.quic = None # QUIC protocol
        self.conn = None # HTTP3 Protocol
        self._push_map = {}
        self._retry = QuicRetryTokenHandler() if self.stateless_retry else None

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
                self._push_map.pop (stream_id)
            except KeyError:
                pass
        super ().remove_request (stream_id)

    def reset_stream (self, stream_id):
        with self._clock:
            for k, v in self._push_map.items ():
                if v == stream_id:
                    return self.cancel_push (k)
        raise AttributeError ('HTTP/3 can cancel for only push stream')

    def remove_push_stream (self, push_id):
        with self._clock:
            try:
                stream_id = self._push_map.pop (push_id)
            except KeyError:
                return
        super ().remove_stream (stream_id)

    def cancel_push (self, push_id):
        with self._clock:
            try:
                steram_id = self._push_map.pop (push_id)
            except KeyError:
                return # already done or canceled
        if stream_id:
            with self._plock:
                if hasattr (self.conn, 'send_cancel_push'):
                    self.conn.send_cancel_push (stream_id)
            self.remove_stream (steram_id)
            self.send_data ()

    def data_to_send (self):
        if self.quic is None or self._closed:
            return []
        self.data_from_producers ()
        with self._plock:
            data_to_send = [data for data, addr in self.quic.datagrams_to_send (now = time.monotonic ())]
        return data_to_send or self.data_exhausted ()

    def _terminate_connection (self):
        # phase II: close quic
        if self.quic:
            errcode, msg = self._shutdown_reason
            self.quic.close (errcode, reason_phrase = msg or '')
            self.send_data ()
        # phase III: close channel
        super ()._terminate_connection ()

    def initiate_shutdown (self, errcode = 0, msg = ''):
        # pahse I: send goaway
        self._shutdown_reason = (errcode, msg)
        if hasattr (self.conn, 'close_connection'):
            with self._plock:
                self.conn.close_connection ()

    def pushable (self):
        return self.request_acceptable ()

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
                self._terminate_connection ()

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
                created = self.handle_request (event.stream_id, event.headers, has_data_frame = not event.stream_ended)
                if created:
                    r = self.get_request (event.stream_id)
                    if event.stream_ended:
                        r.set_stream_ended ()

            elif isinstance(event, DataReceived) and event.data:
                r = self.get_request (event.stream_id)
                if not r:
                    self.close (self.errno.INTERNAL_ERROR)
                else:
                    try:
                        r.channel.set_data (event.data, len (event.data))
                    except ValueError:
                        self.close (self.errno.INTERNAL_ERROR)

                    if event.stream_ended:
                        if r.collector:
                            r.channel.handle_read ()
                            r.channel.found_terminator ()
                        r.set_stream_ended ()
                        if r.response.is_done ():
                            self.remove_request (event.stream_id)

            elif isinstance(event, PushCanceled):
                self.remove_push_stream (event.push_id)
                with self._clock:
                    try:
                        del self._push_map [event.push_id]
                    except KeyError:
                        pass
        self.send_data ()

    def handle_request (self, stream_id, headers, has_data_frame = False):
        if hasattr (self.conn, 'send_duplicate_push'):
            with self._clock:
                pushing = len (self._pushed_pathes)
            if pushing:
                path = None
                for k, v in headers:
                    if k [0] != 58:
                        break
                    elif k == b':method':
                        if v != b"GET":
                            path = None
                            break
                    elif k == b':path':
                        path = v.decode ()
                push_id = None
                with self._clock:
                    push_id = self._pushed_pathes.get (path)
                    if push_id and push_id not in self._push_map:
                        push_id = None # canceled push
                with self._plock:
                    self.conn.send_duplicate_push (stream_id, push_id)
                return False
        return super ().handle_request (stream_id, headers, has_data_frame)

    def push_promise (self, stream_id, request_headers, addtional_request_headers):
        _, path = request_headers [0]
        assert _ == ':path', ':path header missing'
        headers = [(k.encode (), v.encode ()) for k, v in request_headers + addtional_request_headers]
        try:
            promise_stream_id = self.conn.send_push_promise (stream_id = stream_id, headers = headers)
            try:
                push_id = self.conn.get_push_id (promise_stream_id)
            except AttributeError:
                push_id = self.conn._next_push_id - 1
        except NoAvailablePushIDError:
            return
        with self._clock:
            self._push_map [push_id] = promise_stream_id
            self._pushed_pathes [path] = push_id
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
