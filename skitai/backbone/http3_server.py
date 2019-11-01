#----------------------------------------------------------
# Implemetation from:
#   https://blog.grijjy.com/2018/08/29/creating-high-performance-udp-servers-on-windows-and-linux/
# Initialized at: Oct 28, 2019
# Author: Hans Roh
#----------------------------------------------------------

from . import http_server, http_request
import socket
from rs4 import asyncore, asynchat
import os, sys, errno

class http3_channel (http_server.http_channel):
    def __init__ (self, server, data, addr):
        super ().__init__(server, None, addr)
        self.handle_request (data)
        self.set_terminator (None)
        self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
        self.set_reuse_addr ()
        self.bind (self.server.addr)
        self.addr = addr
        self.connect (self.addr)

    def handle_request (self, data):
        r = http_request.http_request (self, "QUiC / HTTP/3.0", "QUiC", "/", "3.0", [])
        self.set_timeout (self.network_timeout)
        self.request_counter.inc()
        self.server.total_requests.inc ()

        for h in self.server.handlers:
            if h.match (r):
                try:
                    h.handle_request (r) # will set self.current_request
                    self.current_request.initiate_connection (data) # collect initial data
                except:
                    self.handle_error ()
                    return

    def readable (self):
        return self.connected

    def handle_connect (self):
        pass

    def recv (self, buffer_size):
        try:
            return super ().recv (buffer_size)
        except ConnectionRefusedError:
            self.handle_close ()
            return b''

    def send (self, data):
        try:
            return super ().send (data)
        except ConnectionRefusedError:
            self.handle_close ()
            return 0

    def collect_incoming_data (self, data):
        self.current_request.collect_incoming_data (data)


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
    VERSION = 'h3-23'

    def __init__ (self, ip, port, ctx, server_logger = None, request_logger = None):
        http_server.http_server.__init__ (self, ip, port, server_logger, request_logger)
        self.ctx = ctx
        self.seesion_store = SessionTicketStore ()

    def _serve (self, shutdown_phase = 2):
        self.shutdown_phase = shutdown_phase

    def readable (self):
        return True

    def recv (self, buffer_size):
        return self.socket.recvfrom (buffer_size)

    def handle_read (self):
        ret = self.recv (self.ac_in_buffer_size)
        if not ret:
            return
        data, addr = ret
        if data:
            http3_channel (self, data, addr)


def init_context (certfile, keyfile, pass_phrase):
    from aioquic.h3.connection import H3_ALPN
    from aioquic.quic.configuration import QuicConfiguration
    import ssl

    ctx = QuicConfiguration (alpn_protocols = H3_ALPN, is_client = False)
    ctx.load_cert_chain (certfile, keyfile, pass_phrase)
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

