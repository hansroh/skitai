from . import http2_handler
import time
import os
from aioquic.quic import events
from aioquic.h3.exceptions import H3Error, NoAvailablePushIDError
from aioquic.buffer import Buffer
from aioquic.quic.packet import PACKET_TYPE_INITIAL, encode_quic_retry, encode_quic_version_negotiation, pull_quic_header
from aioquic.quic.retry import QuicRetryTokenHandler
from aioquic.quic.connection import QuicConnection
import enum
from aquests.protocols.http3.events import PushCanceled, MaxPushIdReceived, DataReceived, HeadersReceived
from aquests.protocols.http3.connection import H3Connection

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
    stateless_retry = True
    conns = {}
    errno = ErrorCode

    def __init__ (self, handler, request):
        self._default_varialbes (handler, request)
        self.quic = None # QUIC protocol
        self.conn = None # HTTP3 Protocol

        self._push_map = {}
        self._retry = QuicRetryTokenHandler() if self.stateless_retry else None

    def _initiate_shutdown (self):
        # pahse I: send goaway
        with self._plock:
            self.conn.shutdown (self._shutdown_reason [-1])

    def _proceed_shutdown (self):
        # phase II: close quic
        if self.quic:
            errcode, msg, _ = self._shutdown_reason
            with self._plock:
                self.quic.close (errcode, reason_phrase = msg or '')
            self.send_data ()

    def _make_connection (self, channel, data):
        # https://github.com/aiortc/aioquic/commits/master/src/aioquic/asyncio/server.py
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

        original_destination_connection_id = None
        retry_source_connection_id = None
        if self._retry is not None:
            source_cid = os.urandom(8)
            if not header.token:
                # create a retry token
                channel.push (
                    encode_quic_retry (
                        version = header.version,
                        source_cid = source_cid,
                        destination_cid = header.source_cid,
                        original_destination_cid = header.destination_cid,
                        retry_token = self._retry.create_token (channel.addr, header.destination_cid, source_cid)))
                return
            else:
                try:
                    original_destination_connection_id, retry_source_connection_id = self._retry.validate_token (channel.addr, header.token)
                except ValueError:
                    return
        else:
            original_destination_connection_id = header.destination_cid

        self.quic = QuicConnection (
            configuration = ctx,
            original_destination_connection_id = original_destination_connection_id,
            retry_source_connection_id = retry_source_connection_id,
            session_ticket_fetcher = channel.server.ticket_store.pop,
            session_ticket_handler = channel.server.ticket_store.add
        )
        self.conn = H3Connection (self.quic)
        self.conn._linked_channel = channel

    def _handle_events (self, events):
        for event in events:
            if isinstance (event, HeadersReceived):
                created = self.handle_request (event.stream_id, event.headers, has_data_frame = not event.stream_ended)
                if created:
                    r = self.get_request (event.stream_id)
                    if event.stream_ended:
                        r.set_stream_ended ()

            elif isinstance (event, DataReceived) and event.data:
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

            elif isinstance (event, PushCanceled):
                with self._clock:
                    try: del self._push_map [event.push_id]
                    except KeyError: pass
                self.remove_push_stream (event.push_id)

        self.send_data ()

    def process_quic_events (self):
        while 1:
            with self._plock:
                event = self.quic.next_event ()
            if event is None:
                break

            if isinstance (event, events.StreamDataReceived):
                h3_events = self.conn.handle_event (event)
                h3_events and self._handle_events (h3_events)

            elif isinstance (event, events.ConnectionIdIssued):
                self.conns [event.connection_id] = self.conn

            elif isinstance (event, events.ConnectionIdRetired):
                assert self.conns [event.connection_id] == self.conn
                conn = self.conns.pop (event.connection_id)
                conn._linked_channel = None

            elif isinstance (event, events.ConnectionTerminated):
                for cid, conn in list (self.conns.items()):
                    if conn == self.conn:
                        conn._linked_channel = None
                        del self.conns [cid]
                self._terminate_connection ()

            elif isinstance (event, events.HandshakeCompleted):
                pass

            elif isinstance (event, events.PingAcknowledged):
                # for now nothing to do, channel will be extened by event time
                pass

    def collect_incoming_data (self, data):
        # print ('collect_incoming_data', self.quic, len (data))
        if self.quic is None:
             self._make_connection (self.channel, data)
             if self.quic is None:
                 return
        with self._plock:
            self.quic.receive_datagram (data, self.channel.addr, time.monotonic ())
        self.process_quic_events ()
        self.send_data ()

    def reset_stream (self, stream_id):
        raise AttributeError ('HTTP/3 can cancel for only push stream, use cancel_push (push_id)')

    def remove_stream (self, stream_id):
        raise AttributeError ('use remove_push_stream (push_id)')

    def remove_push_stream (self, push_id):
        # received by client and just reset
        with self._clock:
            try: stream_id = self._push_map.pop (push_id)
            except KeyError: return
        super ().remove_stream (stream_id)

    def cancel_push (self, push_id):
        # send to client and reset
        with self._clock:
            try: steram_id = self._push_map.pop (push_id)
            except KeyError: return # already done or canceled
        with self._plock:
            self.conn.cancel_push (push_id)
        super ().remove_stream (steram_id)
        self.send_data ()

    def data_to_send (self):
        with self._clock:
            if self.quic is None or self._closed:
                return []
            finished = self._data_from_producers ()
        for stream_id in finished:
            self.remove_request (stream_id)
        with self._plock:
            data_to_send = [data for data, addr in self.quic.datagrams_to_send (now = time.monotonic ())]
        return data_to_send or self._data_exhausted ()

    def pushable (self):
        return self.request_acceptable ()

    def push_promise (self, stream_id, request_headers, addtional_request_headers):
        name_, path = request_headers [0]
        assert name_ == ':path', ':path header missing'
        headers = [(k.encode (), v.encode ()) for k, v in request_headers + addtional_request_headers]
        try:
            promise_stream_id = self.conn.send_push_promise (stream_id = stream_id, headers = headers)
        except NoAvailablePushIDError:
            return

        with self._clock:
            push_id = self._pushed_pathes.get (path)

        if push_id is None:
            try:
                push_id = self.conn.get_push_id (promise_stream_id)
            except AttributeError:
                push_id = self.conn._next_push_id - 1

            with self._clock:
                self._push_map [push_id] = promise_stream_id
                self._pushed_pathes [path] = push_id

        self._handle_events ([HeadersReceived (headers = headers, stream_ended = True, stream_id = promise_stream_id, push_id = push_id)])


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
