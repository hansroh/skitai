from rs4 import asynchat, asyncore
import re, os, sys
import ssl
import socket
import time
import zlib
from warnings import warn
from errno import ECONNRESET, ENOTCONN, ESHUTDOWN, ECONNABORTED, EWOULDBLOCK
if os.name == "nt":
    from errno import WSAENOTCONN
import select
import threading
from .impl.dns import adns
from .impl.http2 import H2_PROTOCOLS
from ..threaded.fifo import await_fifo
from rs4.misc.ssl_ import resolve_cert_reqs, resolve_ssl_version, create_urllib3_context
from collections import deque
from .impl.http import respcodes
from .baseconnect import ConnectProxy, BaseConnect, DEFAULT_ZOMBIE_TIMEOUT, DEFAULT_KEEP_ALIVE
import random

DEBUG = False

class SocketPanic (Exception): pass
class TimeOut (Exception): pass

class ConnectProxy (ConnectProxy):
    def execute_late (self):
        if self._canceled ():
            return
        request, rs, handler, handle_request_failed = self._args
        self._asyncon.set_timeout (self._timeout)
        try:
            self._asyncon.execute (request, rs, handler)
        except:
            handle_request_failed (rs, self._asyncon)
        self._args = None


class AsynConnect (asynchat.async_chat, BaseConnect):
    ac_in_buffer_size = 65535
    ac_out_buffer_size = 65535
    fifo_class = deque
    keep_connect = True
    is_ssl = False

    def __init__ (self, address, lock, logger = None):
        BaseConnect.__init__ (self, lock, logger)

        self.address = address
        self.handler = None

        self.auth = None
        self.proxy = False
        self.initialize_connection ()
        self._closed = False
        self.backend = False

        self.ac_in_buffer = b''
        self.incoming = []
        self.producer_fifo = self.fifo_class ()
        self.set_event_time ()
        self.__sendlock = threading.Lock ()

        asyncore.dispatcher.__init__(self)

    def __repr__ (self):
        return "<AsynConnect %s:%d>" % self.address

    def execute (self, request, rs, handler, *args, **kargs):
        r = handler (self, request, rs.handle_result)
        if self.get_proto () and self.isconnected ():
            self.handler.handle_request (r)
        else:
            r.handle_request ()

    def duplicate (self):
        new_asyncon = self.__class__ (self.address, self.lock, self.logger)
        # used in socketpool
        new_asyncon.proxy = self.proxy
        # used in skitai cluster manager
        new_asyncon.keep_alive = self.keep_alive
        new_asyncon.auth = self.auth
        new_asyncon.backend = self.backend
        new_asyncon.keep_connect = self.keep_connect
        return new_asyncon

    def set_auth (self, auth):
        self.auth = auth

    def get_auth (self):
        return self.auth

    def close (self):
        if self._closed:
            return

        # sometimes socket is not closed at once
        # possibly related with SSL socket
        # then prevent doble callbacking in request_handler
        if self.socket:
            # self.socket is still None, when DNS not found
            asynchat.async_chat.close (self)
            self._fileno = None

        # re-init asychat
        self.ac_in_buffer = b''
        self.incoming = []
        self.producer_fifo.clear()
        self._proto = None
        self._closed = True

        if not self.handler:
            return self.set_active (False)

        if not self.errcode:
            # disconnect intentionally
            return

        handler, self.handller = self.handler, None
        keep_active = False
        try:
            keep_active = handler.connection_closed (self.errcode, self.errmsg)
        except:
            self.trace ()

        if not keep_active:
            if self.errcode not in (704, 712, 722):
                # controlled shutdown
                self.logger (
                    "..socket %s has been closed%s" % ("%s:%d" % self.address, self.errcode != 700 and " (reason: {})".format (self.errcode) or ''),
                    "info"
                )
            self.set_active (False)
            # IMP: DO NOT touch self.handelr
            # IMP: DO NOT CALL end_tran (), not like dbconnect, this is controlled by handler
            # IMP: ensure test level4/test_example_apps_with_aquests.py
        # DO NOT Change any props, because may be request has been restarted

    def end_tran (self):
        # MUST CALL ONLY SUCCESSE, otherwaise already called by self.close ()
        if not self.keep_connect:
            self.disconnect ()
        elif not self.backend:
            self.del_channel ()
        # IMP: DO NOT touch self.handelr
        # IMP: ensure test level4/test_example_apps_with_aquests.py
        self.set_active (False)

    def get_proto (self):
        with self.lock:
            return self._proto

    def set_proto (self, proto):
        with self.lock:
            self._proto = proto

    def initialize_connection (self):
        self._raised_ENOTCONN = 0 # for win32
        self._history = []
        self._proto = None
        self._handshaking = False
        self._handshaked = False

        self.established = False
        self.upgraded = False

    def is_proxy (self):
        return self.proxy

    def log (self, msg, logtype):
        if self.handler is not None and hasattr (self.handler, "log"):
            self.handler.log (msg, logtype)
        elif self.logger:
            self.logger (msg, logtype)
        else:
            warn ("No logger")

    def trace (self):
        if self.handler is not None and hasattr (self.handler, "trace"):
            self.handler.trace ()
        elif self.logger:
            self.logger.trace ()
        else:
            warn ("No logger for traceback")

    def clean_shutdown_control (self, phase, time_in_this_phase):
        self._no_more_request = True
        if self.isactive () or (self.handler and self.handler.working ()):
            return 1
        else:
            self.handle_close (712, "Controlled Shutdown")
            self._no_more_request = False
            return 0

    def is_channel_in_map (self, map = None):
        if map is None:
            map = self._map
        return self._fileno in map

    def isconnected (self):
        with self.lock:
            r = self.connected
        return r

    def del_channel (self, map = None):
        fd = self._fileno
        super ().del_channel (map)
        self._fileno = fd

    def create_socket (self, family, type):
        self.family_and_type = family, type
        sock = socket.socket (family, type)
        sock.setblocking (0)
        self.set_socket (sock)

    def connect (self):
        if adns.query:
            adns.query (self.address [0], "A", callback = self.continue_connect)
        else:
            self.continue_connect ()

    def continue_connect (self, answer = None):
        self.initialize_connection ()
        if not adns.query:
            self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
            try: asynchat.async_chat.connect (self, self.address)
            except:    self.handle_error (714)
            return

        ipaddr = answer [-1]["data"]
        if not ipaddr:
            return self.handle_close (704)
        else:
            port = self.address [1]

        self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
        try:
            asynchat.async_chat.connect (self, (ipaddr, port))
        except:
            self.handle_error (714)

    def recv (self, buffer_size):
        try:
            data = self.socket.recv (buffer_size)
            if not data:
                self.handle_close (700, "Connection closed unexpectedly in recv")
                return b''
            else:
                self.set_event_time ()
                return data
        except socket.error as why:
            if why.errno in asyncore._DISCONNECTED:
                self.handle_close (700, "Connection closed unexpectedly in recv")
                return b''
            else:
                raise

    def send (self, data):
        try:
            numsent = self.socket.send (data)
            if numsent:
                self.set_event_time ()
            return numsent

        except socket.error as why:
            if why.errno == EWOULDBLOCK:
                return 0
            elif why.errno in asyncore._DISCONNECTED:
                if os.name == "nt" and why.errno == asyncore.ENOTCONN:
                    # winsock sometimes raise ENOTCONN and sometimes recovered.
                    # Found this error at http://file.hungryboarder.com:8080/HBAdManager/pa.html?siteId=hboarder&zoneId=S-2
                    if self._raised_ENOTCONN <= 3:
                        self._raised_ENOTCONN += 1
                        return 0
                    else:
                        self._raised_ENOTCONN = 0
                self.handle_close (700, "Connection closed unexpectedly in send")
                return 0
            else:
                raise

    def close_if_over_keep_live (self):
        if time.time () - self.event_time > self.keep_alive:
            self.disconnect ()

    def set_keep_alive (self, keep_alive = 10):
        self.keep_alive = keep_alive

    def handle_connect (self):
        if hasattr (self.handler, "has_been_connected"):
            self.handler.has_been_connected ()

    def handle_expt (self):
        self.handle_close (703)

    def handle_error (self, code = 701):
        self.trace ()
        self.handle_close (code)

    def handle_timeout (self):
        self.handle_close (702)

    def handle_expt_event (self):
        err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err != 0:
            self.handle_close (703, "Socket %d Error" % err)
        else:
            self.handle_expt ()

    def maintern (self, object_timeout):
        if time.time () - self.event_time > object_timeout:
            if self.handler:
                if hasattr (self.handler, "control_shutdown"):
                    self.handler.control_shutdown ()
                self.handle_close (722)
            else:
                self.disconnect ()
            return True
        return False

    def writable (self):
        with self.__sendlock:
            return self.producer_fifo or (not self.connected)

    def handle_write (self):
        with self.__sendlock:
            self.initiate_send ()

    # proxy POST need no init_send
    def push (self, thing, init_send = True):
        if self.connected:
            self.close_if_over_keep_live () # check keep-alive

        if isinstance(thing, (bytes, bytearray, memoryview)):
            with self.__sendlock:
                asynchat.async_chat.push (self, thing)
        else:
            self.push_with_producer (thing, init_send)

    def push_with_producer (self, producer, init_send = True):
        if self.connected:
            self.close_if_over_keep_live () # check keep-alive

        with self.__sendlock:
            self.producer_fifo.append (producer)
            if init_send:
                self.initiate_send ()

    def handle_abort (self):
        self.handle_close (706)

    def handle_close (self, code = 700, msg = ""):
        if code == 0: msg = ""
        self.errcode = code
        if msg:
            self.errmsg = msg
        else:
            self.errmsg = respcodes.get (code, "Undefined Error")
        self.close ()

    def collect_incoming_data (self, data):
        if not self.handler:
            if self.connected:
                self.logger ("recv data but no handler, droping data %d" % len (data), "warn")
                self.disconnect ()
            return
        self.handler.collect_incoming_data (data)

    def found_terminator (self):
        if not self.handler:
            if self.connected:
                self.logger ("found terminator but no handler", "warn")
                self.disconnect ()
            return # already closed
        self.handler.found_terminator ()

    def disconnect (self):
        self.errcode = 0
        self.close ()

    def reconnect (self):
        self.disconnect ()
        self.connect ()

    def set_proxy (self, flag = True):
        self.proxy = flag

    def begin_tran (self, handler):
        if self._no_more_request:
            return self.handle_close (705)
        # IMP: the reason why DNS error, _closed must be located here
        self._closed = False
        self.errcode = 0
        self.errmsg = ""

        self.handler = handler
        if DEBUG:
            self.logger ('begin_tran {rid:%s} %s' % (self.handler.request.meta.get ('req_id', -1), self.handler.request.uri), 'debug')

        self.set_event_time ()
        try:
            if not self.connected:
                self.connect ()
            elif not self.backend:
                self.add_channel ()
        except:
            self.handle_error ()


class AsynSSLConnect (AsynConnect):
    is_ssl = True

    def __init__ (self, address, lock = None, logger = None):
        AsynConnect.__init__ (self, address, lock, logger)
        self.ac_negotiate_http2 = True

    def negotiate_http2 (self, flag):
        self.ac_negotiate_http2 = flag

    def handshake (self):
        if not self._handshaking:
            err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if err != 0:
                raise OSError(err, asyncore._strerror(err))

            ssl_context = create_urllib3_context(ssl_version=resolve_ssl_version(None), cert_reqs=resolve_cert_reqs(None))
            if self.ac_negotiate_http2:
                try: ssl_context.set_alpn_protocols (H2_PROTOCOLS)
                except AttributeError: ssl_context.set_npn_protocols (H2_PROTOCOLS)
            self.socket = ssl_context.wrap_socket (self.socket, do_handshake_on_connect = False, server_hostname = self.address [0])
            self._handshaking = True

        try:
            self.socket.do_handshake ()
        except ssl.SSLError as why:
            if why.args [0] in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                return False
            raise ssl.SSLError(why)

        try: self._proto = self.socket.selected_alpn_protocol()
        except (AttributeError, NotImplementedError):
            try: self._proto = self.socket.selected_npn_protocol()
            except (AttributeError, NotImplementedError): pass

        self._handshaked = True
        return True

    def handle_connect_event (self):
        try:
            if not self._handshaked and not self.handshake ():
                return
        except:
            return self.handle_error (713)
        AsynConnect.handle_connect_event (self)

    def recv (self, buffer_size):
        if self._closed:
            # usually handshaking failure, already handled exception
            return b''

        try:
            data = self.socket.recv (buffer_size)
            if not data:
                self.handle_close (700, "Connection closed unexpectedly")
                return b''
            else:
                self.set_event_time ()
                return data

        except ssl.SSLError as why:
            if why.errno == ssl.SSL_ERROR_WANT_READ:
                try:
                    raise BlockingIOError
                except NameError:
                    raise socket.error (EWOULDBLOCK)

            # closed connection
            elif why.errno in (ssl.SSL_ERROR_ZERO_RETURN, ssl.SSL_ERROR_EOF):
                self.handle_close (700, "Connection closed by SSL_ERROR_ZERO_RETURN or SSL_ERROR_EOF")
                return b''

            else:
                raise

    def send (self, data):
        if self._closed:
            # usually handshaking failure, already handled exception
            return

        try:
            numsent = self.socket.send (data)
            if numsent:
                self.set_event_time ()
            return numsent

        except ssl.SSLError as why:
            if why.errno == ssl.SSL_ERROR_WANT_WRITE:
                return 0
            elif why.errno == ssl.SSL_ERROR_ZERO_RETURN:
                self.handle_close (700, "Connection closed by SSL_ERROR_ZERO_RETURN")
                return 0
            else:
                raise


class AsynSSLProxyConnect (AsynSSLConnect, AsynConnect):
    is_ssl = True

    def __init__ (self, address, lock = None, logger = None):
        AsynConnect.__init__ (self, address, lock, logger)

    def handle_connect_event (self):
        if self.established:
            AsynSSLConnect.handle_connect_event (self)
        else:
            AsynConnect.handle_connect_event (self)

    def recv (self, buffer_size):
        if self._handshaked or self._handshaking:
            return AsynSSLConnect.recv (self, buffer_size)
        else:
            return AsynConnect.recv (self, buffer_size)

    def send (self, data):
        if self._handshaked or self._handshaking:
            return AsynSSLConnect.send (self, data)
        else:
            return AsynConnect.send (self, data)

