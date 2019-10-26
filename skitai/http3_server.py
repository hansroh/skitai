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

class http3_channel (https_server.https_channel):
    def __init__ (self, server, data, addr):
        http_server.http_channel.__init__(self, server, None, addr)
        self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
        self.connect (addr)


class http3_server (https_server.https_server):
    def create_socket (self, stack):
        super ().create_socket (stack, socket.SOCK_DGRAM)

    def _serve (self, shutdown_phase = 2):
        self.shutdown_phase = shutdown_phase

    def handle_connect(self):
        pass

    def handle_read (self):
        ret = self.recv (self.buffer_size)
        if not ret:
            return
        data, addr = ret
        if data:
            http3_channel (self, data, addr)

    def recv (self, buffer_size):
        try:
            return self.socket.recvfrom (buffer_size)
        except MemoryError:
            lifetime.shutdown (1, 1.0)

        except ssl.SSLError as why:
            if why.errno == ssl.SSL_ERROR_WANT_READ:
                try:
                    raise BlockingIOError
                except NameError:
                    raise socket.error (EWOULDBLOCK)
            # closed connection
            elif why.errno in (ssl.SSL_ERROR_ZERO_RETURN, ssl.SSL_ERROR_EOF):
                self.handle_close ()
                return None
            else:
                raise

