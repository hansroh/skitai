#!/usr/bin/env python

from . import http_server
from ..counter import counter
import socket, time
from rs4 import asyncore
import ssl
from skitai import lifetime
import os, sys, errno
import skitai
from errno import EWOULDBLOCK
from rs4.protocols.sock.impl.http2 import H2_PROTOCOLS
from ..handlers import vhost_handler

class https_channel (http_server.http_channel):
    ac_out_buffer_size = 65536
    ac_in_buffer_size = 65536

    def send(self, data):
        try:
            result = self.socket.send(data)

        except (ConnectionRefusedError, ConnectionResetError):
            self.handle_close ()
            return 0

        except ssl.SSLError as why:
            if why.errno == ssl.SSL_ERROR_WANT_WRITE:
                return 0
            elif why.errno == ssl.SSL_ERROR_ZERO_RETURN:
                self.handle_close ()
                return 0
            else:
                raise

        if result <= 0:
            return 0
        else:
            self.bytes_out.inc (result)
            self.server.bytes_out.increment(result)
            return result

    def recv(self, buffer_size = 65535):
        try:
            result = self.socket.recv(buffer_size)
            if result is None:
                return b''

            elif result == b'':
                self.handle_close()
                return b''

            else:
                lr = len(result)
                self.server.bytes_in.inc (lr)
                self.bytes_in.inc (lr)
                return result

        except MemoryError:
            lifetime.shutdown (1, 1.0)

        except (ConnectionRefusedError, ConnectionResetError):
            self.handle_close ()
            return b''

        except ssl.SSLError as why:
            if why.errno == ssl.SSL_ERROR_WANT_READ:
                try:
                    raise BlockingIOError
                except NameError:
                    raise socket.error (EWOULDBLOCK)
            # closed connection
            elif why.errno in (ssl.SSL_ERROR_ZERO_RETURN, ssl.SSL_ERROR_EOF):
                self.handle_close ()
                return b''
            else:
                raise


class https_server (http_server.http_server):
    CERTINFO = None
    def __init__ (self, ip, port, ctx, quic = None, server_logger = None, request_logger = None):
        super ().__init__ (ip, port, server_logger, request_logger)
        self.ctx = ctx
        self.socket = self.ctx.wrap_socket (self.socket, server_side = True)
        if quic:
            if os.name == 'nt' or sys.version_info < (3, 7):
                self.log ('unsupported Python version or system for QUIC, DISABLED', 'error')
            else:
                from . import http3_server
                ctx = http3_server.init_context (*self.CERTINFO)
                self.altsvc = http3_server.http3_server (ip, quic, port, ctx, server_logger, request_logger)

    def install_handler (self, handler, back = 1):
        super ().install_handler (handler, back)
        if self.altsvc and isinstance (handler, vhost_handler.Handler):
            self.altsvc.install_handler (handler)

    def serve (self, sub_server = None, backlog = 100):
        self.altsvc and self.altsvc._serve ()
        super ().serve (sub_server, backlog)

    def handle_accept (self):
        self.total_clients.inc()

        try:
            conn, addr = self.accept()
        except socket.error:
            #self.log_info ('server accept() threw an exception', 'warning')
            return
        except TypeError:
            if os.name == "nt":
                self.log_info ('server accept() threw EWOULDBLOCK', 'warning')
            return
        except:
            self.trace()
        https_channel (self, conn, addr)


def init_context (certfile, keyfile, pass_phrase):
    https_server.CERTINFO = (certfile, keyfile, pass_phrase)
    try:
        protocol = ssl.PROTOCOL_TLS
    except AttributeError:
        protocol = ssl.PROTOCOL_SSLv23
    ctx = ssl.SSLContext (protocol)
    try:
        ctx.set_alpn_protocols (H2_PROTOCOLS)
    except AttributeError:
        ctx.set_npn_protocols (H2_PROTOCOLS)
    ctx.load_cert_chain (certfile, keyfile, pass_phrase)
    ctx.check_hostname = False
    return ctx
