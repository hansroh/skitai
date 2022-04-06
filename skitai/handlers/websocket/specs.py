import threading
import json
import skitai
from .. import wsgi_handler
from ...protocols.threaded import trigger
from ...protocols.sock.impl.grpc import discover
from ...protocols.sock.impl.http import http_util
from skitai import version_info, was as the_was
import xmlrpc.client as xmlrpclib
from urllib.parse import quote_plus
from io import BytesIO
import copy
from rs4.misc.reraise import reraise
from collections.abc import Iterable
from ...protocols.sock.impl.ws.collector import Collector as BaseWebsocketCollector
from ...protocols.sock.impl.ws.collector import encode_message
try:
    from werkzeug.wsgi import ClosingIterator
except ImportError:
    ClosingIterator = None
from ...protocols.sock.impl.ws import *
import time

class WebSocket (BaseWebsocketCollector):
    collector = None
    producer = None

    def __init__ (self, handler, request, message_encoding = None):
        super ().__init__ (message_encoding)
        self.handler = handler
        self.wasc = handler.wasc
        self.request = request
        self.channel = request.channel
        self.channel.set_terminator (2)
        self._closed = False
        self.encoder_config = None
        self.message_encoding = self.setup_encoding (message_encoding)

    def close (self):
        if self._closed: return
        self._closed = True

    def closed (self):
        return self._closed

    def setup_encoding (self, message_encoding):
        if message_encoding == skitai.WS_MSG_GRPC:
            i, o = discover.find_type (self.request.uri [1:])
            self.encoder_config = (i [0], 0 [0])
            self.default_op_code = OPCODE_BINARY
            self.message_encode = self.grpc_encode
            self.message_decode = self.grpc_decode
        elif message_encoding == skitai.WS_MSG_JSON:
            self.message_encode = json.dumps
            self.message_decode = json.loads
        elif message_encoding == skitai.WS_MSG_XMLRPC:
            self.message_encode = xmlrpclib.dumps
            self.message_decode = xmlrpclib.loads
        else:
            self.message_encode = self.transport
            self.message_decode = self.transport
        return message_encoding

    def transport (self, msg):
        return msg

    def grpc_encode (self, msg):
        f = self.encoder_config [0] ()
        f.ParseFromString (msg)
        return f

    def grpc_decode (self, msg):
        return msg.SerializeToString ()

    def build_data (self, message, op_code):
        message = self.message_encode (message)
        if op_code == -1:
            if type (message) is str:
                op_code = OPCODE_TEXT
            elif type (message) is bytes:
                op_code = OPCODE_BINARY
            if op_code == -1:
                op_code = self.default_op_code
        return message, op_code

    def send (self, messages, op_code = -1):
        if ClosingIterator and isinstance (messages, ClosingIterator): # for werkzeug iterator
            messages = [ b''.join ([msg for msg in messages]).decode ("utf8") ]
        elif isinstance (messages, (str, bytes)) or not isinstance (messages, Iterable):
            messages = [ messages ]
        for msg in messages:
            self.sendone (msg, op_code)
    write = send

    def sendone (self, message, op_code = -1):
        if not self.channel: return
        message, op_code = self.build_data (message, op_code)
        m = encode_message (message, op_code)
        self._send (m)

    def _send (self, msg):
        if self.channel:
            if hasattr (self.wasc, 'threads'):
                trigger.wakeup (lambda p=self.channel, d=msg: (p.push (d),))
            else:
                self.channel.push (msg)

    def handle_message (self, msg):
        raise NotImplementedError ("handle_message () not implemented")

#---------------------------------------------------------

class Job (wsgi_handler.Job):
    def exec_app (self):
        env = self.args [0]
        was = the_was._get () # get from current thread
        env ["skitai.was"] = was
        was.request = self.request
        was.env = env
        was.websocket = env ["websocket"]

        try:
            content = self.apph (*self.args)
        except:
            was.traceback ()
            was.websocket.channel and was.websocket.channel.close ()
        else:
            if content:
                if type (content) is not tuple:
                    content = (content,)
                was.websocket.send (*content)

#---------------------------------------------------------

class WebSocket1 (WebSocket):
    # WEBSOCKET_REQDATA
    def __init__ (self, handler, request, apph, env, param_names, message_encoding = None):
        WebSocket.__init__ (self, handler, request, message_encoding)
        self.client_id = request.channel.channel_number
        self.apph = apph
        self.param_names = param_names
        self.env = env
        self.session = env.get ("websocket.session")
        self.set_query_string ()

    def start_response (self, message, headers = None, exc_info = None):
        if exc_info:
            reraise (*exc_info)

    def set_query_string (self):
        if not self.param_names:
            self.querystring = ""
            self.params = {}
            return

        querystring = []
        if self.env.get ("QUERY_STRING"):
            querystring.append (self.env.get ("QUERY_STRING"))
        querystring.append ("%s=" % self.param_names [0])
        self.querystring = "&".join (querystring)
        self.params = http_util.crack_query (self.querystring)

    def open (self):
        self.handle_message (-1, skitai.WS_EVT_OPEN)
        if "websocket.handler" in self.env:
            app = self.apph.get_callable ()
            app.register_websocket (self.client_id, self.send)

    def close (self):
        if "websocket.handler" in self.env:
            app = self.apph.get_callable ()
            app.remove_websocket (self.client_id)
        if not self.closed ():
            self.handle_message (-1, skitai.WS_EVT_CLOSE)
            WebSocket.close (self)

    def make_params (self, msg, event):
        querystring = self.querystring
        params = self.params
        if event:
            self.env ['websocket.event'] = event
        else:
            self.env ['websocket.event'] = None
            querystring = querystring + quote_plus (msg)
            params [self.param_names [0]] = self.message_decode (msg)
        return querystring, params

    def handle_message (self, msg, event = None):
        if not msg:
            return
        if self.session:
            self.handle_session (msg, event)
        else:
            self.handle_thread (msg, event)

    def handle_session (self, msg, event):
        if event:
            if event == skitai.WS_EVT_CLOSE:
                try:
                    next (self.session)
                    resp = self.session.send (None)
                except:
                    return
            else:
                return

        next (self.session)
        resp = self.session.send (msg)
        if resp:
            if isinstance (resp, str):
                resp = [resp]
            [ self.send (m) for m in resp ]

    def handle_thread (self, msg, event = None):
        querystring, params = self.make_params (msg, event)
        self.env ["QUERY_STRING"] = querystring
        self.env ["websocket.params"] = params
        self.env ["websocket.client"] = self.client_id
        self.execute ()

    def execute (self):
        args = (self.request, self.apph, (self.env, self.start_response), None, self.wasc.logger)
        if not self.env ["wsgi.multithread"]:
            Job (*args) ()
        else:
            self.wasc.queue.put (Job (*args))


class WebSocket6 (WebSocket1):
    def __init__ (self, handler, request, apph, env, param_names, message_encoding = None):
        WebSocket1.__init__ (self, handler, request, apph, env, param_names, message_encoding)
        self.lock = threading.Lock ()

    def _send (self, msg):
        with self.lock:
            WebSocket1._send (self, msg)


class WebSocket5 (WebSocket1):
    # WEBSOCKET_MULTICAST CLIENT
    def __init__ (self, handler, request, server, env, param_names):
        self.server = server
        WebSocket1.__init__ (self, handler, request, server.apph, env, param_names)

    def handle_message (self, msg, event = None):
        self.server.handle_client (self.client_id, event)
        WebSocket1.handle_message (self, msg, event)

