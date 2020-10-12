#!/usr/bin/env python

import sys
from rs4 import asyncore, asynchat
import re, socket, time, threading, os
from . import http_request
from .. import counter
from aquests.protocols.http import http_util, http_date
from aquests.athreads import threadlib
from skitai import lifetime
from rs4 import producers, compressors
from rs4.termcolor import tc
from collections import deque
import signal
import ssl
import skitai
from hashlib import md5
from rs4.psutil import kill
from rs4.psutil.processutil import set_process_name, drop_privileges
from ..exceptions import HTTPError

if os.name == "posix":
    import psutil
    CPUs = psutil.cpu_count()

PID = {}
ACTIVE_WORKERS = 0
SURVAIL = True
EXITCODE = 0
DEBUG = False
IS_DEVEL = os.environ.get ('SKITAIENV') == "DEVEL"
ON_SYSTEMD = os.environ.get ("DAEMONIZER") == 'systemd'
IS_TTY = sys.stdout.isatty ()

#-------------------------------------------------------------------
# server channel
#-------------------------------------------------------------------
class http_channel (asynchat.async_chat):
    current_request = None
    channel_count = counter.counter ()
    closed = False
    is_rejected = False

    keep_alive = 30
    network_timeout = 30
    zombie_timeout = 30

    fifo_class = deque
    multi_threaded = False

    closed_channels = []
    closed_channel_reported = 0.0

    def __init__ (self, server, conn, addr):
        self.conn = conn
        self.server = server
        self.channel_number = http_channel.channel_count.inc ()
        self.request_counter = counter.counter()
        self.bytes_out = counter.counter()
        self.bytes_in = counter.counter()

        self.ac_in_buffer = b''
        self.incoming = []
        self.producer_fifo = self.fifo_class ()
        asyncore.dispatcher.__init__(self, conn)
        self.addr = addr # SHOULD place after asyncore.dispatcher.__init__
        self.set_terminator (b'\r\n\r\n')
        self.in_buffer = b''
        self.creation_time = int (time.time())
        self.event_time = int (time.time())
        self.producers_attend_to = []
        self.things_die_with = []

        self.__sendlock  = threading.Lock ()
        self.__history = []

    def get_history (self):
        return self.__history

    def reject (self):
        self.is_rejected = True

    def initiate_send (self):
        super ().initiate_send ()
        try:
            is_working = self.producer_fifo.working ()
        except AttributeError:
            is_working = len (self.producer_fifo)
        if not is_working:
            self.done_request ()

    def writable (self):
        with self.__sendlock:
            return len (self.producer_fifo) or (not self.connected)

    def handle_write (self):
        with self.__sendlock:
            self.initiate_send ()

    def link_protocol_writer (self):
        self.writable = self.writable_with_protocol
        self.handle_write = self.handle_write_with_protocol

    def writable_with_protocol (self):
        with self.__sendlock:
            has_fifo = len (self.producer_fifo)
        return has_fifo or (self.current_request and self.current_request.has_sendables ())

    def handle_write_with_protocol (self):
        try:
            data_to_send = self.current_request.data_to_send ()
        except AttributeError:
            # self.current_request is None
            return False
        [self.push (data) for data in data_to_send]
        if not data_to_send:
            # anyway call eventually
            with self.__sendlock:
                self.initiate_send ()
            return False
        return True

    def push (self, data):
        with self.__sendlock:
            super ().push (data)

    def push_with_producer (self, producer):
        with self.__sendlock:
            super ().push_with_producer (producer)

    def readable (self):
        return not self.is_rejected and asynchat.async_chat.readable (self)

    def issent (self):
        return self.bytes_out.as_long ()

    def __repr__ (self):
        ar = asynchat.async_chat.__repr__(self) [1:-1]
        return '<%s channel#: %s-%s requests:%s>' % (
                ar,
                self.server.worker_ident,
                self.channel_number,
                self.request_counter
                )

    def clean_shutdown_control (self, phase, time_in_this_phase):
        if phase == 3:
            self.reject ()
            if self.writable ():
                return 1
            self.close ()
            return 0

    def isconnected (self):
        return self.connected

    def handle_timeout (self):
        IS_TTY and self.log ("killing zombie channel %s" % ":".join (map (str, self.addr)))
        self.close ()

    def set_timeout (self, timeout):
        self.zombie_timeout = timeout

    def set_socket_timeout (self, timeout):
        self.keep_alive = timeout
        self.network_timeout = timeout

    def attend_to (self, thing):
        if not thing: return
        self.producers_attend_to.append (thing)

    def die_with (self, thing, tag):
        if not thing: return
        self.things_die_with.append ((thing, tag))

    def done_request (self):
        self.producers_attend_to = [] # all producers are finished
        self.set_timeout (self.keep_alive)

    def send (self, data):
        # print ("SEND", len (data))
        self.event_time = int (time.time())
        result = asynchat.async_chat.send (self, data)
        self.server.bytes_out.inc (result)
        self.bytes_out.inc (result)
        return result

    def recv (self, buffer_size):
        self.event_time = int (time.time())
        try:
            result = asynchat.async_chat.recv (self, buffer_size)
            if not result:
                self.handle_close ()
                return b""
            # print ("RECV", len (result), self.get_terminator ())
            lr = len (result)
            self.server.bytes_in.inc (lr)
            self.bytes_in.inc (lr)
            return result

        except MemoryError:
            lifetime.shutdown (1, 1.0)

    def collect_incoming_data (self, data):
        #print ("collect_incoming_data", repr (data [:180]), self.current_request)
        if self.current_request:
            self.current_request.collect_incoming_data (data)
        else:
            self.in_buffer = self.in_buffer + data

    def forward_domain (self, r):
        host = r.get_header ('host', '').split (":", 1)[0]
        if host == self.server.single_domain:
            return False
        scheme, port = r.get_scheme (), self.server.port
        if (scheme == 'https' and port == 443) or (scheme == 'http' and port == 80):
            port = ""
        else:
            port = ":{}".format (port)
        newloc = '{}://{}{}{}'.format (scheme, self.server.single_domain, port, r.uri)
        r.response.set_header ("Location", newloc)
        r.response.error (301, why = "Object moved to <a href='{}'>here</a>".format (newloc))
        return True

    def found_terminator (self):
        if self.is_rejected:
            return

        if self.current_request:
            self.current_request.found_terminator()
            if DEBUG:
                self.__history.append ("REQUEST DONE")
                self.__history = self.__history [-30:]

        else:
            header = self.in_buffer
            self.in_buffer = b''
            lines = header.decode ("utf8").split('\r\n')
            while lines and not lines[0]:
                lines = lines[1:]

            if not lines:
                self.close_when_done()
                return

            request = lines[0]
            try:
                command, uri, version = http_util.crack_request (request)
            except:
                self.log_info ("channel %s-%s invalid request header" % (self.server.worker_ident, self.channel_number), "fail")
                return self.close ()

            if DEBUG:
                self.__history.append ("START REQUEST: %s/%s %s" % (command, version, uri))

            header = http_util.join_headers (lines[1:])
            r = http_request.http_request (self, request, command, uri, version, header)
            if self.server.single_domain and self.forward_domain (r):
                return
            self.set_timeout (self.network_timeout)
            self.request_counter.inc()
            self.server.total_requests.inc()

            if command is None:
                r.response.error (400)
                return

            for h in self.server.handlers:
                if h.match (r):
                    try:
                        self.current_request = r
                        h.handle_request (r)

                    except HTTPError as e:
                        r.response.error (e.status)

                    except:
                        self.server.trace()
                        try: r.response.error (500)
                        except: pass

                    return

            try: r.response.error (404)
            except: pass

    def handle_abort (self):
        self.close (ignore_die_partner = True)
        self.log_info ("channel %s-%s aborted" % (self.server.worker_ident, self.channel_number), "info")

    def close (self, ignore_die_partner = False):
        global IS_DEVEL

        if self.closed:
            return

        for closable, tag in self.things_die_with:
            if closable and hasattr (closable, "channel"):
                closable.channel = None
            self.journal (tag)
            if not ignore_die_partner:
                self.producers_attend_to.append (closable)

        if self.current_request is not None:
            self.producers_attend_to.append (self.current_request.collector)
            self.producers_attend_to.append (self.current_request.producer)
            # 1. close forcely or by error, make sure that channel is None
            # 2. by close_when_done ()
            self.current_request.channel = None
            self.current_request = None

        for closable in self.producers_attend_to:
            if closable and hasattr (closable, "close"):
                try:
                    closable.close ()
                except:
                    self.server.trace()

        self.producers_attend_to, self.things_die_with = [], []
        self.discard_buffers ()
        asynchat.async_chat.close (self)
        self.connected = False
        self.closed = True

        http_channel.closed_channels.append ("%s-%s" % (self.server.worker_ident, self.channel_number))
        now = time.time ()
        if now - http_channel.closed_channel_reported > 3.0:
            IS_TTY and self.log_info ("%d channels closed" % len (http_channel.closed_channels), "info")
            http_channel.closed_channels = []
            http_channel.closed_channel_reported = now

    def journal (self, reporter):
        self.log (
            "%s closed, client %s:%s, bytes in: %s, bytes out: %s for %d seconds " % (
                reporter,
                self.addr [0],
                self.addr [1],
                self.bytes_in,
                self.bytes_out,
                time.time () - self.creation_time
            )
        )

    def log (self, message, type = "info"):
        self.server.log (message, type)
    log_info = log

    def trace (self, id = None):
        self.server.trace (id)

    def handle_expt(self):
        self.log_info ("channel %s-%s panic" % (self.server.worker_ident, self.channel_number), "fail")
        self.close ()

    def handle_error (self):
        self.server.trace ("channel %s-%s" % (self.server.worker_ident, self.channel_number))
        self.close()


#-------------------------------------------------------------------
# server class
#-------------------------------------------------------------------
class http_server (asyncore.dispatcher):
    SERVER_IDENT = skitai.NAME
    KEEP_PRIVILEGES = False

    maintern_interval = 0
    critical_point_cpu_overload = 90.0
    critical_point_continuous = 3
    altsvc = None
    sock_type = socket.SOCK_STREAM

    def __init__ (self, ip, port, server_logger = None, request_logger = None):
        global PID

        self.handlers = []
        self.ip = ip
        self.port = port
        asyncore.dispatcher.__init__ (self)

        if ip.find (":") != -1:
            self.create_socket (socket.AF_INET6)
        else:
            self.create_socket (socket.AF_INET)

        self.set_reuse_addr ()
        try:
            self.bind ((ip, port))
        except OSError as why:
            if why.errno == 98:
                server_logger ("address already in use, cannot start server", "fatal")
            else:
                server_logger.trace ()
            sys.exit (0)

        self.worker_ident = "master"
        self.server_logger = server_logger
        self.request_logger = request_logger
        self.start_time = time.ctime(time.time())
        self.start_time_int = time.time()

        self.total_clients = counter.counter()
        self.total_requests = counter.counter()
        self.exceptions = counter.counter()
        self.bytes_out = counter.counter()
        self.bytes_in  = counter.counter()
        self.shutdown_phase = 2

        self.__last_maintern = time.time ()

        host, port = self.socket.getsockname()
        hostname = socket.gethostname()
        try:
            self.server_name = socket.gethostbyaddr (hostname)[0]
        except socket.error:
            self.server_name = hostname
        self.hash_id = md5 (self.server_name.encode ('utf8')).hexdigest() [:4]
        self.server_port = port
        self.single_domain = None

    def set_single_domain (self, domain):
        self.single_domain = domain

    def _serve (self, shutdown_phase = 2, backlog = 100):
        self.shutdown_phase = shutdown_phase
        self.listen (backlog)

    def serve (self, sub_server = None, backlog = 100):
        if sub_server:
            sub_server._serve (max (1, self.shutdown_phase - 1))
        self._serve (backlog = 100)

    def fork (self, numworker = 1):
        global ACTIVE_WORKERS, SURVAIL, PID, EXITCODE

        if os.name == "nt":
            set_process_name (skitai.get_proc_title ())
            signal.signal(signal.SIGTERM, hTERMWORKER)

        else:
            while SURVAIL:
                try:
                    if ACTIVE_WORKERS < numworker:
                        pid = os.fork ()
                        if pid == 0:
                            if os.name != 'nt' and not self.KEEP_PRIVILEGES:
                                drop_privileges (skitai.SERVICE_USER, skitai.SERVICE_GROUP)
                            self.worker_ident = "w%d" % len (PID)
                            set_process_name ("%s:%s" % (skitai.get_proc_title (), self.worker_ident))
                            PID = {}
                            signal.signal(signal.SIGTERM, hTERMWORKER)
                            signal.signal(signal.SIGQUIT, hQUITWORKER)
                            signal.signal(signal.SIGHUP, hHUPWORKER)
                            break

                        else:
                            set_process_name ("%s:m" % skitai.get_proc_title ())
                            if not PID:
                                signal.signal(signal.SIGHUP, hHUPMASTER)
                                signal.signal(signal.SIGTERM, hTERMMASTER)
                                signal.signal(signal.SIGINT, hTERMMASTER)
                                signal.signal(signal.SIGQUIT, hQUITMASTER)
                                signal.signal (signal.SIGCHLD, hCHLD)

                            ps = psutil.Process (pid)
                            ps.x_overloads = 0
                            PID [pid] = ps
                            ACTIVE_WORKERS += 1

                    now = time.time ()
                    if self.maintern_interval and now - self.__last_maintern > self.maintern_interval:
                        self.maintern (now)
                    time.sleep (1)

                except KeyboardInterrupt:
                    EXITCODE = 0
                    DO_SHUTDOWN (signal.SIGTERM)
                    break

            if self.worker_ident == "master":
                kill.child_processes_gracefully () # killing multiprocessing.semaphore_tracker
                return EXITCODE

        self.log_info ('%s%s started on %s:%s' % (
            hasattr (self, 'ctx') and 'SSL ' or '',
            tc.blue ('worker #' + self.worker_ident [1:]), self.server_name, tc.white (self.port)
        ))
        if self.altsvc:
            self.log_info ('QUIC %s started on %s:%s' % (
                tc.blue ('worker #' + self.worker_ident [1:]), self.server_name, tc.white (self.altsvc.port)
            ))

    usages = []
    cpu_stat = []
    def maintern (self, now):
        global PID, CPUs

        self.__last_maintern = now
        usages = []
        for pid, ps in PID.items ():
            if ps is None:
                continue
            try:
                usage = ps.cpu_percent ()
            except (psutil.NoSuchProcess, AttributeError):
                # process changed, maybe next time
                usage = 0.0
            usages.append ((ps, usage))

        if not usages:
            # restarting?
            return

        self.usages.append (sum ([x [1] for x in usages]) / len (usages))
        self.usages = self.usages [-45:]
        self.cpu_stat = []
        max_usage = 0
        for c in (3, 15, 45):
            # 1m, 5m, 15
            array = self.usages [-c:]
            self.cpu_stat.append ((max (array), int (sum (array) / c)))

        if self.cpu_stat [0][0] > 10:
            # 60% for 1m
            self.log ("CPU percent: " + ", ".join (["%d/%d" % unit for unit in self.cpu_stat]))

        for ps, usage in usages:
            if usage < self.critical_point_cpu_overload:
                ps.x_overloads = 0 #reset count
                continue

            ps.x_overloads += 1
            if ps.x_overloads > self.critical_point_continuous:
                self.log ("process %d is overloading, try to kill..." % ps.pid, 'fatal')
                sig = ps.x_overloads > (self.critical_point_continuous + 2) and signal.SIGKILL or signal.SIGTERM
                try:
                    kill.child_processes_gracefully (ps.pid)
                except:
                    self.trace ('worker pid: {}'.format (ps.pid))

    def create_socket(self, family):
        if hasattr (socket, "_no_timeoutsocket"):
            sock_class = socket._no_timeoutsocket
        else:
            sock_class = socket.socket

        self.family_and_type = family, self.sock_type
        sock = sock_class (family, self.sock_type)
        sock.setblocking(0)
        self.set_socket(sock)

    def clean_shutdown_control (self, phase, time_in_this_phase):
        if phase == self.shutdown_phase:
            self.log_info ('shutting down web server: %s' % self.server_name)
            self.close ()

    def close (self):
        asyncore.dispatcher.close (self)
        for h in self.handlers:
            if hasattr (h, "close"):
                h.close ()

    def writable (self):
        return 0

    def install_handler (self, handler, back = 1):
        if back:
            self.handlers.append (handler)
        else:
            self.handlers.insert (0, handler)

    def remove_handler (self, handler):
        self.handlers.remove (handler)

    def log (self, message, type = "info"):
        if self.server_logger:
            self.server_logger.log (message, type)
        else:
            sys.stdout.write ('log: [%s] %s\n' % (type,str (message)))

    def log_request (self, message):
        if self.request_logger:
            self.request_logger.log (message, "")
        else:
            sys.stdout.write ('%s\n' % message)

    def log_info(self, message, type='info'):
        self.log (message, type)

    def trace (self, id = None):
        self.exceptions.inc()
        if self.server_logger:
            self.server_logger.trace (id)
        else:
            asyncore.dispatcher.handle_error (self)

    def handle_read (self):
        pass

    def readable (self):
        return self.accepting

    def handle_error (self):
        self.trace()

    def handle_connect (self):
        pass

    def handle_accept (self):
        self.total_clients.inc()
        try:
            conn, addr = self.accept()
        except socket.error:
            self.log_info ('server accept() threw an exception', 'warn')
            return
        except TypeError:
            if os.name == "nt":
                self.log_info ('server accept() threw EWOULDBLOCK', 'warn')
            return

        http_channel (self, conn, addr)

    def handle_expt (self):
        self.log_info ('socket panic', 'warning')

    def handle_close (self):
        self.log_info('server shutdown', 'warning')
        self.close()

    def status (self):
        global PID

        return     {
            "child_pids": list (PID.keys ()),
            "ident": "%s for %s" % (self.worker_ident, self.SERVER_IDENT),
            'server_name': self.server_name,
            "start_time": self.start_time,
            'hash_id': self.hash_id,
            "port": self.port,
            "total_clients": self.total_clients.as_long(),
            "total_request": self.total_requests.as_long(),
            "total_exceptions": self.exceptions.as_long(),
            "bytes_out": self.bytes_out.as_long(),
            "bytes_in": self.bytes_in.as_long(),
            "cpu_percent":    self.cpu_stat
        }

def hCHLD (signum, frame):
    global ACTIVE_WORKERS, PID

    ACTIVE_WORKERS -= 1
    try:
        pid, status = os.waitpid (0, 0)
    except ChildProcessError:
        pass
    else:
        PID [pid] = None

def hTERMWORKER (signum, frame):
    lifetime.shutdown (0, 1.0)

def hHUPWORKER (signum, frame):
    lifetime.shutdown (3, 1.0)

def hQUITWORKER (signum, frame):
    lifetime.shutdown (0, 30.0)

def DO_SHUTDOWN (sig):
    global PID

    signal.signal (signal.SIGCHLD, signal.SIG_IGN)
    for pid in PID:
        if PID [pid] is None:
            continue
        try: os.kill (pid, sig)
        except OSError: pass

def hTERMMASTER (signum, frame):
    global EXITCODE, SURVAIL
    SURVAIL = False
    EXITCODE = 0
    DO_SHUTDOWN (signal.SIGTERM)

def hQUITMASTER (signum, frame):
    global EXITCODE
    EXITCODE = 0
    DO_SHUTDOWN (signal.SIGQUIT)

def hHUPMASTER (signum, frame):
    global PID
    for pid in PID:
        if PID [pid] is None:
            continue
        try: os.kill (pid, signal.SIGHUP)
        except OSError: pass


def configure (name, network_timeout = 0, keep_alive = 0, multi_threaded = False, max_upload_size = 256000000):
    from . import https_server
    from ..handlers.http2 import request as http2_request

    http_request.http_request.max_upload_size = max_upload_size
    http2_request.request.max_upload_size = max_upload_size

    http_server.SERVER_IDENT = name
    https_server.https_server.SERVER_IDENT = name
    channels = [http_channel, https_server.https_channel]

    try:
        from . import http3_server
    except ImportError:
        pass
    else:
        http3_server.http3_server.SERVER_IDENT = name
        channels.append (http3_server.http3_channel)

    for channel in channels:
        channel.keep_alive = not keep_alive and 2 or keep_alive
        channel.network_timeout = not network_timeout and 30 or network_timeout
        channel.multi_threaded = multi_threaded


if __name__ == "__main__":
    pass
