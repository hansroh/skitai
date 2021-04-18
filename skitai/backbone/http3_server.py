#----------------------------------------------------------
# Implemetation from:
#   https://blog.grijjy.com/2018/08/29/creating-high-performance-udp-servers-on-windows-and-linux/
# Initialized at: Oct 28, 2019
# Author: Hans Roh
#----------------------------------------------------------

from . import http_server, https_server, http_request
import socket
from rs4 import asyncore, asynchat
import os, sys, errno
import time
from .lifetime import tick_timer

class http3_channel (https_server.https_channel, http_server.http_channel):
    def __init__ (self, server, data, addr):
        http_server.http_channel.__init__(self, server, None, addr)
        self.initial_data = data
        self.protocol = None # quic

        self._timer_at = None
        self._timer_id = None
        self.create_handler ()
        self.set_terminator (None)
        self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
        self.set_reuse_addr ()
        self.bind (self.server.addr)
        self.addr = addr # bind change addr, so recovering
        self.connect (self.addr)

    def writable (self):
        return self.writable_with_protocol ()

    def readable (self):
        return self.connected

    def handle_write (self):
        # https://github.com/aiortc/aioquic/blob/master/src/aioquic/asyncio/protocol.py
        # transmit (self)
        written = self.handle_write_with_protocol ()
        if written and self.protocol:
            # re-arm timer
            timer_at = self.protocol.get_timer()
            if self._timer_id is not None and self._timer_at != timer_at:
                tick_timer.cancel (self._timer_id)
                self._timer_id = None
            if self._timer_id is None and timer_at is not None:
                self._timer_id = tick_timer.at (timer_at, self.handle_timer)
            self._timer_at = timer_at

    def handle_timer (self):
        # https://github.com/aiortc/aioquic/blob/master/src/aioquic/asyncio/protocol.py
        # _handle_timer (self)
        if not self.current_request:
            return
        now = max (self._timer_at, time.monotonic ())
        self._timer_id = None
        self._timer_at = None
        self.protocol.handle_timer (now = now)
        self.current_request.process_quic_events ()
        self.handle_write ()

    def recv (self, buffer_size):
        try:
            return http_server.http_channel.recv (self, buffer_size)
        except (ConnectionRefusedError, ConnectionResetError):
            self.handle_close ()
            return b''

    def send (self, data):
        try:
            return http_server.http_channel.send (self, data)
        except (ConnectionRefusedError, ConnectionResetError):
            self.handle_close ()
            return 0

    # packet handler -----------------------------------------------------------
    def create_handler (self):
        r = http_request.http_request (self, "QUIC / HTTP/3.0", "QUIC", "/", "3.0", [])
        self.set_timeout (self.network_timeout)
        self.request_counter.inc()
        self.server.total_requests.inc ()

        for h in self.server.handlers:
            if h.match (r):
                try:
                    h.handle_request (r) # will set self.current_request
                except:
                    self.handle_error ()
                    return

    def handle_connect (self):
        self.collect_incoming_data (self.initial_data) # collect initial data
        self.initial_data = None

    def collect_incoming_data (self, data):
        self.current_request.collect_incoming_data (data)
        if self.protocol is None:
            self.protocol = self.current_request.quic


class SessionTicketStore:
    def __init__(self):
        self.tickets = {}

    def add(self, ticket):
        self.tickets [ticket.ticket] = ticket

    def pop(self, label):
        return self.tickets.pop (label, None)


class http3_server (http_server.http_server):
    ac_in_buffer_size = 65536
    sock_type = socket.SOCK_DGRAM
    PROTOCOLS = []
    ALTSVC_HEADER = ''

    def __init__ (self, ip, port, ssl_port, ctx, server_logger = None, request_logger = None):
        http_server.http_server.__init__ (self, ip, port, server_logger, request_logger)
        self.ssl_port = ssl_port
        self.ctx = ctx
        self.PROTOCOLS = self.ctx.alpn_protocols
        self.ALTSVC_HEADER = ', '.join (['{}=":{}"; ma=86400'.format (p, self.ssl_port) for p in self.PROTOCOLS])
        self.ticket_store = SessionTicketStore ()

    def _serve (self, shutdown_phase = 2):
        self.shutdown_phase = shutdown_phase

    def readable (self):
        return True

    def recv (self, buffer_size):
        try:
            return self.socket.recvfrom (buffer_size)
        except (ConnectionResetError, BlockingIOError):
            return b''

    def handle_read (self):
        ret = self.recv (self.ac_in_buffer_size)
        if not ret:
            return
        data, addr = ret
        if data:
            http3_channel (self, data, addr)

AIOQUIC_REQUIRED = (0, 9)

def init_context (certfile, keyfile, pass_phrase):
    import aioquic
    assert tuple (map (int, aioquic.__version__.split (".") [:2])) >= AIOQUIC_REQUIRED, "aioquic version >= {} required".format (".".join (map (str, AIOQUIC_REQUIRED)))
    from aioquic.h3.connection import H3_ALPN
    from aioquic.quic.configuration import QuicConfiguration
    import ssl

    ctx = QuicConfiguration (alpn_protocols = H3_ALPN, is_client = False)
    ctx.load_cert_chain (certfile, keyfile, pass_phrase)
    ctx.verify_mode = ssl.CERT_NONE
    return ctx
