#!/usr/bin/env python

from . import http_server
from .counter import counter
import socket, time
from rs4 import asyncore
import ssl
from skitai import lifetime
import os, sys, errno
import skitai
from errno import EWOULDBLOCK
import collections

class http3_channel (http_server.http_channel):
    def __init__ (self, server, data, addr):
        self.initial_data = data
        super ().__init__(server, None, addr)
        self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
        self.connect (addr)

    def readable (self):
        return False

    def send (self, data):
        self.server.push (data, self.addr)
        return len (data)

    def handle_connect (self):
        self.push (b'echo:' + self.initial_data)


class http3_server (http_server.http_server):
    ac_in_buffer_size = 65536
    ac_out_buffer_size = 65536
    sock_type = socket.SOCK_DGRAM

    def __init__ (self, ip, port, ctx, server_logger = None, request_logger = None):
        http_server.http_server.__init__ (self, ip, port, server_logger, request_logger)
        self.queue = collections.deque ()
        self.ctx = ctx
        # self.socket = self.ctx.wrap_socket (self.socket, server_side = True)

    def _serve (self, shutdown_phase = 2):
        self.shutdown_phase = shutdown_phase

    def send (self, data, addr):
        try:
            result = self.socket.sendto (data, addr)
            return result
        except OSError as why:
            if why.args[0] == EWOULDBLOCK:
                return 0
            elif why.args[0] in asyncore._DISCONNECTED:
                self.handle_close()
                return 0
            else:
                raise

    def initiate_send (self):
        data, addr = self.queue.popleft ()
        sendto, data = data [:self.ac_out_buffer_size], data [self.ac_out_buffer_size:]
        num_sent = self.send (sendto, addr)
        data = sendto [num_sent:] + data
        if data:
            self.queue.append ((data, addr))

    def handle_write(self):
        self.initiate_send ()

    def push (self, data, addr):
        self.queue.append ((data, addr))
        self.initiate_send()

    def writable (self):
        return len (self.queue)

    def readable (self):
        return True

    def handle_read (self):
        ret = self.recv (self.ac_in_buffer_size)
        if not ret:
            return
        data, addr = ret
        if data:
            http3_channel (self, data, addr)

    def recv (self, buffer_size):
        return self.socket.recvfrom (buffer_size)
