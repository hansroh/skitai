import skitai
from . import wsgi_handler
from h2.connection import H2Connection, H2Configuration
from h2.exceptions import ProtocolError, StreamClosedError, FlowControlError
from h2.events import TrailersReceived, DataReceived, RequestReceived, StreamEnded, PriorityUpdated, ConnectionTerminated, StreamReset, RemoteSettingsChanged
from h2.settings import SettingCodes
from .http2.request import request as http2_request
from .http2.vchannel import fake_channel, data_channel
from aquests.protocols.http2.request_handler import FlowControlWindow
import threading
from io import BytesIO
import time
import enum
from rs4 import producers

# http3 compat error codes
class ErrorCodes (enum.IntEnum):
    NO_ERROR = 0x0
    PROTOCOL_ERROR = 0x1
    INTERNAL_ERROR = 0x2
    FLOW_CONTROL_ERROR = 0x3
    CANCEL = 0x8

class http2_producer:
    SIZE_BUFFER = 16384
    def __init__ (self, conn, lock, stream_id, headers, producer, trailers, depends_on = 0, priority = 1, log_hook = None):
        self.conn = conn
        self.lock = lock
        self.stream_id = stream_id
        self.headers = headers
        self.producer = producer
        self.trailers = trailers
        self.depends_on = depends_on
        self.priority = priority
        self.log_hook = log_hook
        self.bytes = 0
        self.next_data = None
        self._end_stream = False
        self._last_sent = time.time ()

    def __lt__ (self, other):
        if self.depends_on == other.depends_on:
            return self.priority > other.priority # descending
        return self.depends_on < other.depends_on # ascending

    def set_stream_ended (self):
        self._end_stream = True

    def is_stream_ended (self):
        return self._end_stream

    def log (self):
        self.log_hook and self.log_hook (self.bytes)

    def send_final_data (self, data):
        with self.lock:
            self.conn.send_data (self.stream_id, data, end_stream = not self.trailers)
            if self.trailers:
                self.conn.send_headers (self.stream_id, self.trailers, end_stream = True)
        self.log ()

    def local_flow_control_window (self):
        lfcw = self.conn.local_flow_control_window (self.stream_id)
        if lfcw == 0:
            # flow control error, graceful close
            if time.time () - self._last_sent > 10:
                raise FlowControlError
        return lfcw

    def produce (self):
        if self.is_stream_ended ():
            return 0
        lfcw = self.local_flow_control_window ()
        if not lfcw:
            return 0

        self._last_sent = time.time ()
        sent = 0
        if self.headers:
            with self.lock:
                self.conn.send_headers (self.stream_id, self.headers, end_stream = not self.producer and not self.trailers)
            self.headers = None
            sent = 1

        if not self.producer:
            self.set_stream_ended ()
            self.log ()
            return sent

        if self.next_data:
            data, self.next_data = self.next_data, None
        else:
            if hasattr (self.producer, 'ready') and not self.producer.ready ():
                return sent
            data = self.producer.more ()
            if not data:
                self.set_stream_ended ()
                self.send_final_data (b'')
                return 1

        avail_data_length = min (self.SIZE_BUFFER, lfcw)
        if len (data) > avail_data_length:
            data, self.next_data = data [:avail_data_length], data [avail_data_length:]

        self.bytes += len (data)
        if self.next_data is None and (not hasattr (self.producer, 'ready') or self.producer.ready ()):
            self.next_data = self.producer.more ()
            if not self.next_data:
                self.set_stream_ended ()

        if self.is_stream_ended ():
            self.send_final_data (data)
        else:
            with self.lock:
                self.conn.send_data (self.stream_id, data, end_stream = False)
        return 1

class http2_request_handler (FlowControlWindow):
    collector = None
    producer = None
    http11_terminator = 24
    producer_class = http2_producer
    altsvc = None
    errno = ErrorCodes

    def __init__ (self, handler, request):
        self.handler = handler
        self.wasc = handler.wasc
        self.request = request
        self.channel = request.channel
        self.conn = H2Connection (H2Configuration (client_side = False))

        self.frame_buf = self.conn.incoming_buffer
        self.frame_buf.max_frame_size = self.conn.max_inbound_frame_size
        self.data_length = 0
        self.current_frame = None
        self.rfile = BytesIO ()
        self.buf = b""
        self._got_preamble = False
        self._close_pending = False
        self.default_varialbes ()
        self.altsvc = request.channel.server.altsvc

    def default_varialbes (self):
        self.producers = []
        self.requests = {}
        self.priorities = {}
        self._has_sendables = False
        self._closed = False
        self._plock = threading.Lock () # for self.conn
        self._clock = threading.Lock () # for self.x

    def send_data (self):
        self._has_sendables = True

    def has_sendables (self):
        return self._has_sendables

    def data_from_producers (self):
        for i in range (len (self.producers)):
            with self._clock:
                try:
                    producer = self.producers [0]
                except IndexError:
                    # maybe removed by reset stream
                    break

            produced = producer.produce ()
            if producer.is_stream_ended ():
                with self._clock:
                    try:
                        self.producers.pop (0)
                    except IndexError:
                        # maybe removed by reset stream
                        break
                r = self.get_request (producer.stream_id)
                self.remove_request (producer.stream_id)

            if produced:
                break
            with self._clock:
                self.producers.append (self.producers.pop (0))
            continue

    def data_exhausted (self):
        close_pending = False
        with self._clock:
            if not self.producers:
                self._has_sendables, close_pending = False, self._close_pending
        close_pending and self.terminate_connection ()
        return [] # MUST return

    def data_to_send (self):
        if self._closed:
            return []
        self.data_from_producers ()
        with self._plock:
            data_to_send = self.conn.data_to_send ()
        return data_to_send and [data_to_send] or self.data_exhausted ()

    def terminate_connection (self):
        if self.channel:
            self.channel.close_when_done ()
        with self._clock:
            self._close_pending = False
            self._closed = True

    def initiate_shutdown (self, errcode = 0, msg = None):
        with self._plock:
            self.conn.close_connection (errcode, msg)

    def close (self, errcode = 0x0, msg = None):
        with self._clock:
            if self._closed:
                return
            self._close_pending = True
        if self.conn:
            self.initiate_shutdown ()
        if self.channel:
            self.send_data ()
        else:
           self.terminate_connection ()

    def enter_shutdown_process (self):
        self.close ()

    def closed (self):
        return self._closed

    def handle_preamble (self):
        if self.request.version.startswith ("2."):
            self.channel.set_terminator (6) # SM\r\n\r\n

    def initiate_connection (self):
        self.handle_preamble ()
        h2settings = self.request.get_header ("HTTP2-Settings")
        if h2settings:
            self.conn.initiate_upgrade_connection (h2settings)
        else:
            self.conn.initiate_connection()
        self.send_data ()
        if self.request.version == "1.1":
            self.handle_request (1, self.upgrade_header ())

    def upgrade_header (self):
        headers = [
            (":method", self.request.command.upper ()),
            (":path", self.request.uri),
        ]
        for line in self.request.get_header ():
            try:
                k, v = line.split (": ", 1)
            except ValueError:
                k, v = line.split (":", 1)
            k = k.lower ()
            if k in ("http2-settings", "connection", "upgrade"):
                continue
            headers.append ((k, v))
        return headers

    def collect_incoming_data (self, data):
        #print ("RECV", repr (data), len (data), '::', self.channel.get_terminator ())
        if not data:
            # closed connection
            self.close ()
            return

        if self.data_length:
            self.rfile.write (data)
        else:
            self.buf += data

    def set_frame_data (self, data):
        if not self.current_frame:
            return []
        self.current_frame.parse_body (memoryview (data))
        self.current_frame = self.frame_buf._update_header_buffer (self.current_frame)
        with self._plock:
            events = self.conn._receive_frame (self.current_frame)
        return events

    def set_terminator (self, terminator):
        self.channel.set_terminator (terminator)

    def found_terminator (self):
        buf, self.buf = self.buf, b""

        #print ("FOUND", repr (buf), '::', self.data_length, self.channel.get_terminator ())
        #print ("FOUND", self.request.version, self.request.command, self.data_length)
        events = None
        if self.request.version == "1.1" and self.data_length:
            self.request.version = "2.0" # upgrade
            data = self.rfile.getvalue ()
            with self._clock:
                r = self.requests [1]
            r.channel.set_data (data, len (data))
            r.set_stream_ended ()
            self.data_length = 0
            self.rfile.seek (0)
            self.rfile.truncate ()
            self.channel.set_terminator (24) # for premble

        elif not self._got_preamble:
            if not buf.endswith (b"SM\r\n\r\n"):
                raise ProtocolError ("Invalid preamble")
            self._got_preamble = True
            self.channel.set_terminator (9)

        elif self.data_length:
            events = self.set_frame_data (self.rfile.getvalue ())
            self.current_frame = None
            self.data_length = 0
            self.rfile.seek (0)
            self.rfile.truncate ()
            self.channel.set_terminator (9) # for frame header

        elif buf:
            self.current_frame, self.data_length = self.frame_buf._parse_frame_header (buf)
            self.frame_buf.max_frame_size = self.data_length

            if self.data_length == 0:
                events = self.set_frame_data (b'')
            self.channel.set_terminator (self.data_length == 0 and 9 or self.data_length)    # next frame header

        else:
            raise ProtocolError ("Frame decode error")

        if events:
            self.handle_events (events)

    def request_acceptable (self):
        with self._clock:
            if self._close_pending or self._closed:
                return False
        return True

    def pushable (self):
        return self.request_acceptable () and self.conn.remote_settings [SettingCodes.ENABLE_PUSH]

    def push_promise (self, stream_id, request_headers, addtional_request_headers):
        promise_stream_id = self.conn.get_next_available_stream_id ()
        headers = request_headers + addtional_request_headers
        with self._plock:
            self.conn.push_stream (stream_id, promise_stream_id, headers)
        event = RequestReceived ()
        event.stream_id = promise_stream_id
        event.headers = headers
        self.handle_events ([event])

    def handle_response (self, stream_id, headers, trailers, producer, do_optimize, force_close = False):
        with self._clock:
            try:
                depends_on, weight = self.priorities [stream_id]
            except KeyError:
                depends_on, weight = 0, 1
            else:
                del self.priorities [stream_id]

        if self.altsvc:
            headers.append (("alt-svc", self.altsvc.ALTSVC_HEADER))

        if trailers:
            assert producer, "http/2 or 3's trailser requires body"
        if producer and do_optimize:
            producer = producers.globbing_producer (producer)

        r = self.get_request (stream_id)
        if r:
            self.producers.append (self.producer_class (self.conn, self._plock, stream_id, headers, producer, trailers, depends_on, weight, r.response.maybe_log))
            self.producers.sort ()
            self.send_data ()

        force_close and self.close (self.errno.FLOW_CONTROL_ERROR)

    def remove_request (self, stream_id):
        r = self.get_request (stream_id)
        if not r: return
        with self._clock:
            try: del self.requests [stream_id]
            except KeyError: pass
        r.protocol = None

    def get_request (self, stream_id):
        r = None
        with self._clock:
            try: r =    self.requests [stream_id]
            except KeyError: pass
        return r

    def adjust_flow_control_window (self, stream_id):
        if self.conn.inbound_flow_control_window < self.MIN_IBFCW:
            with self._clock:
                self.conn.increment_flow_control_window (1048576)

        rfcw = self.conn.remote_flow_control_window (stream_id)
        if rfcw < self.MIN_RFCW:
            try:
                with self._clock:
                    self.conn.increment_flow_control_window (1048576, stream_id)
            except StreamClosedError:
                pass

    def handle_events (self, events):
        for event in events:
            if isinstance(event, RequestReceived):
                self.handle_request (event.stream_id, event.headers, has_data_frame = not event.stream_ended)

            elif isinstance(event, TrailersReceived):
                self.handle_trailers (event.stream_id, event.headers)

            elif isinstance(event, StreamReset):
                if event.remote_reset:
                    self.remove_stream (event.stream_id)

            elif isinstance(event, ConnectionTerminated):
                self.terminate_connection ()

            elif isinstance(event, PriorityUpdated):
                if event.exclusive:
                    # rebuild depend_ons
                    for stream_id in list (self.priorities.keys ()):
                        depends_on, weight = self.priorities [stream_id]
                        if depends_on == event.depends_on:
                            self.priorities [stream_id] = [event.stream_id, weight]

                with self._clock:
                    self.priorities [event.stream_id] = [event.depends_on, event.weight]

            elif isinstance(event, DataReceived):
                r = self.get_request (event.stream_id)
                if not r:
                    self.close (self.errno.INTERNAL_ERROR)
                else:
                    try:
                        r.channel.set_data (event.data, event.flow_controlled_length)
                    except ValueError:
                        # from vchannel.handle_read () -> collector.collect_inconing_data ()
                        self.close (self.errno.INTERNAL_ERROR)
                    else:
                        self.adjust_flow_control_window (event.stream_id)

            elif isinstance(event, StreamEnded):
                r = self.get_request (event.stream_id)
                if r:
                    if r.collector:
                        r.channel.handle_read ()
                        r.channel.found_terminator ()
                    r.set_stream_ended ()
                    if r.response.is_done ():
                        # DO NOT REMOVE before responsing:
                        # this is for async streaming request like proxy request
                        self.remove_request (event.stream_id)

        self.send_data ()

    def remove_stream (self, stream_id):
        r = self.get_request (stream_id)
        if r and r.collector:
            try: r.collector.stream_has_been_reset ()
            except AttributeError: pass
            r.set_stream_ended ()
            self.remove_request (stream_id)

        with self._clock:
            for i in range (len (self.producers)):
                if self.producers [i].stream_id == stream_id:
                    self.producers.pop (i)
                    break

    def reset_stream (self, stream_id, errcode = ErrorCodes.CANCEL):
        closed = False
        with self._plock:
            try:
                self.conn.reset_stream (stream_id, error_code = errcode)
            except StreamClosedError:
                closed = True
        if not closed:
            self.remove_stream (stream_id)
        self.send_data ()

    def handle_trailers     (self, stream_id, headers):
        r = self.get_request (stream_id)
        for k, v in headers:
            r.header.append (
                "{}: {}".format (k.decode ("utf8"), v.decode ("utf8"))
            )

    def handle_request (self, stream_id, headers, has_data_frame = False):
        if not self.request_acceptable ():
            return

        #print ("++REQUEST: %d" % stream_id, headers)
        command = "GET"
        uri = "/"
        scheme = "http"
        authority = ""
        cl = 0
        h = []
        cookies = []

        if type (headers [0][0]) is bytes:
            headers = [(k.decode ("utf8"), v.decode ("utf8")) for k, v in headers]

        for k, v in headers:
            #print ('HEADER:', k, v)
            if k[0] == ":":
                if k == ":method": command = v.upper ()
                elif k == ":path": uri = v
                elif k == ":scheme": scheme = v.lower ()
                elif k == ":authority":
                    authority = v
                    if authority:
                        h.append ("host: %s" % authority.lower ())
                continue
            if k == "content-length":
                cl = int (v)
            elif k == "cookie":
                cookies.append (v)
                continue
            h.append ("%s: %s" % (k, v))

        if cookies:
            h.append ("Cookie: %s" % "; ".join (cookies))

        should_have_collector = False
        if command == "CONNECT":
            first_line = "%s %s HTTP/%s" % (command, authority, self.request.version)
            vchannel = self.channel
        else:
            first_line = "%s %s HTTP/%s" % (command, uri, self.request.version)
            if command in ("POST", "PUT", "PATCH"):
                should_have_collector = True
                if not cl and has_data_frame:
                    # dummy content-lengng for data frames
                    cl = -1
                    h.append ('content-length: {}'.format (cl))
                vchannel = data_channel (stream_id, self.channel, cl)
            else:
                if stream_id == 1:
                    self.request.version = "2.0"
                vchannel = fake_channel (stream_id, self.channel)

        r = http2_request (
            self,  scheme, stream_id,
            vchannel, first_line, command.lower (), uri, self.request.version, h
        )
        vchannel.current_request = r
        with self._clock:
            self.channel.request_counter.inc()
            self.channel.server.total_requests.inc()

        h = self.handler.default_handler
        if not h.match (r):
            try: r.response.error (404)
            except: pass
            return

        with self._clock:
            self.requests [stream_id] = r

        try:
            h.handle_request (r)

        except:
            self.channel.server.trace()
            try: r.response.error (500)
            except: pass

        else:
            if should_have_collector and cl > 0:
                if r.collector is None:
                    # POST but too large body or 3xx, 4xx
                    if stream_id == 1 and self.request.version == "1.1":
                        self.channel.close_when_done ()
                        self.remove_request (1)
                    else:
                        self.close (self.errno.FLOW_CONTROL_ERROR)
                else:
                    if stream_id == 1 and self.request.version == "1.1":
                        self.data_length = cl
                        self.set_terminator (cl)


class h2_request_handler (http2_request_handler):
    http11_terminator = None

    def handle_preamble (self):
        if self.request.version.startswith ("2."):
            self.conn.receive_data ("PRI * HTTP/2.0\r\n\r\n")
            self.channel.set_terminator (None)

    def collect_incoming_data (self, data):
        with self._plock:
            events = self.conn.receive_data (data)
        self.handle_events (events)


class Handler (wsgi_handler.Handler):
    keep_alive = 37 # chrome QUIC timout is prox. 30

    def __init__(self, wasc, default_handler = None):
        wsgi_handler.Handler.__init__(self, wasc, None)
        self.default_handler = default_handler

    def match (self, request):
        return True

    def handle_request (self, request):
        is_http2 = False
        if request.command == "pri" and request.uri == "*" and request.version == "2.0":
            is_http2 = True
        else:
            upgrade = request.get_header ("upgrade")
            is_http2 = upgrade and upgrade.lower () == "h2c" and request.version == "1.1"

        if not is_http2:
            return self.default_handler.handle_request (request)

        http2 = http2_request_handler (self, request)
        request.channel.die_with (http2, "http2 connection")
        request.channel.set_socket_timeout (self.keep_alive)

        if request.version == "1.1":
            request.response (
                "101 Switching Protocol",
                headers = [("Connection",  "upgrade"), ("Upgrade", "h2c"), ("Server", skitai.NAME.encode ("utf8"))]
            )
            request.response.done (upgrade_to = (http2, http2.http11_terminator))
        else:
            request.channel.current_request = http2

        request.channel.link_protocol_writer ()
        http2.initiate_connection ()
