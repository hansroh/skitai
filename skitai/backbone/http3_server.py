#----------------------------------------------------------
# Implemetation from:
#   https://blog.grijjy.com/2018/08/29/creating-high-performance-udp-servers-on-windows-and-linux/
# Initialized at: Oct 28, 2019
# Author: Hans Roh
#----------------------------------------------------------

from . import http_server
import socket
from rs4 import asyncore, asynchat
import os, sys, errno
from ..handlers import http3_handler

if os.name == 'nt':
    class http3_channel:
        pass

    class http3_server:
        pass

else:
    class http3_channel (http_server.http_channel):
        def __init__ (self, server, data, addr):
            super ().__init__(server, None, addr)            
            self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
            self.set_reuse_addr ()
            self.bind (self.server.addr)            
            self.current_handler = http3_handler.http3_request_handler (self)     
            self.current_handler.initiate_connection ()
            self.set_terminator (4) # frame type, definitely setting frame
            self.find_terminator (data) # collect initial data
            self.connect (self.addr)            

        def bind(self, addr):
            # removed: self.addr = addr
            return self.socket.bind (addr)

        def readable (self):
            return self.connected

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
            self.current_handler.collect_incoming_data (data)
            
        def found_terminator (self):
            self.current_request.find_terminator ()
            
        def handle_connect (self):
            pass


    class http3_server (http_server.http_server):
        ac_in_buffer_size = 65536
        ac_out_buffer_size = 65536
        sock_type = socket.SOCK_DGRAM

        def __init__ (self, ip, port, ctx, server_logger = None, request_logger = None):
            http_server.http_server.__init__ (self, ip, port, server_logger, request_logger)
            self.ctx = ctx
            # self.socket = self.ctx.wrap_socket (self.socket, server_side = True)

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

