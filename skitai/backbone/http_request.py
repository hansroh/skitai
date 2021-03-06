from . import http_response
from .. import counter
import time
import re
try:
    import ujson as json
except ImportError:
    import json
from rs4.attrdict import CaseInsensitiveDict
from aquests.protocols.http import http_util
from rs4 import jwt

class JWTUser:
    def __init__ (self, claims):
        self.__claims = claims

    @property
    def name (self):
        return self.__claims ["username"]

    def __getattr__ (self, attr):
        return self.__claims.get (attr)

    def __str__ (self):
        return self.name

class http_request:
    response_class = http_response.http_response
    version = "1.1"
    collector = None
    producer = None
    request_count = counter.counter()

    def __init__ (self, *args):
        self.request_number = self.request_count.inc()
        (self.channel, self.request,
         self.command, self.uri, self.version,
         self.header) = args
        self.logger = self.channel.server.server_logger
        self.server_ident = self.channel.server.SERVER_IDENT
        self.body = None
        self.multipart = None
        self.reply_code = 200
        self.reply_message = ""
        self.loadbalance_retry = 0
        self.rbytes = 0
        self.created = time.time ()
        self.gzip_encoded = False
        self._split_uri = None
        self._headers_cache = None
        self._header_cache = {}
        self._is_stream_ended = False
        self._is_async_streaming = False
        self._is_promise = False
        self._xmlrpc_serialized = False # used by testuitl.client
        self._jwt = None
        self.args = {}

        self.PARAMS = {}
        self.URL = {}
        self.JSON = None
        self.FORM = None
        self.set_log_info ()
        self.make_response ()

    def _override_defaults (self, dict):
        if "defaults" in self.routable:
            for k, v in self.routable ["defaults"].items ():
                if k not in dict:
                    dict [k] = v
        return dict

    def set_args (self, args):
        self.args = self._override_defaults (args)

    @property
    def DEFAULT (self):
        try:
            return self.routable ["defaults"]
        except KeyError:
            pass

    @property
    def JWT (self):
        return self._jwt or self.dejwt ()

    @property
    def method (self):
        return self.command.upper ()

    @property
    def scheme (self):
        return self.get_scheme ()

    @property
    def headers (self):
        if self._headers_cache:
            return self._headers_cache
        h = CaseInsensitiveDict ()
        for line in self.header:
            k, v = line.split (":", 1)
            h [k] = v.strip ()
        self._headers_cache = h
        return h

    @property
    def payload (self):
        return self.get_body ()

    def dejwt (self, token = None, salt = None):
        if not token:
            if self._jwt:
                return self._jwt
            token_ = self.get_header ("authorization")
            if not token_ or token_ [:7].lower () != "bearer ":
                self._jwt = {"err": "no bearer token"}
                return self._jwt
            token = token_ [7:]

        try:
            claims = jwt.get_claim (salt or self.salt, token)
        except (TypeError, ValueError):
            claims = {"err": "invalid token"}
        else:
            if claims is None:
                claims = {"err": "invalid signature"}
            else:
                now = time.time ()
                if claims ["exp"] < now:
                    claims = {"err": "token expired"}
                elif "nbf" in claims and claims ["nbf"] > now:
                    claims = {"err": "token not activated yet"}

        self._jwt = claims
        if "username" in claims:
            self.user = JWTUser (claims)
        return claims

    def json (self, ct = None):
        if not ct:
            ct = self.get_header ('content-type', '')
        if not ct.startswith ("application/json"):
            return
        if self.JSON is not None:
            return self.JSON
        self.JSON = json.loads (self.body.decode ('utf8'))
        return self.JSON

    def form (self, ct = None):
        if self.FORM is not None:
            return self.FORM
        if not ct:
            ct = self.get_header ('content-type', '')
        if self.multipart:
            self.FORM = self.multipart
        elif ct.startswith ("application/x-www-form-urlencoded"):
            self.FORM = http_util.crack_query (self.body)
        return self.FORM

    def dict (self):
        if not self.multipart and not self.body:
            return {}
        ct = self.get_header ('content-type', '')
        maybe = self.json (ct)
        if maybe is None:
            maybe = self.form (ct)
        return maybe or {}

    @property
    def DATA (self):
        return self.dict ()

    @property
    def ARGS (self):
        return self.args

    def set_multipart (self, dict):
        self.multipart = dict

    def get_multipart (self):
        return self.multipart

    def set_body (self, body):
        self.body = body

    def get_body (self):
        return self.body
    get_payload = get_body

    def is_promise (self):
        return self._is_promise

    def make_response (self):
        self.response = self.response_class (self)

    def set_streaming (self):
            self._is_async_streaming = True

    def is_async_streaming (self):
        return self._is_async_streaming

    def set_stream_ended (self):
        self._is_stream_ended = True

    def is_stream_ended (self):
        return self._is_stream_ended

    def set_log_info (self):
        self.gtxid = self.get_header ("X-Gtxn-Id")
        if not self.gtxid:
            self.gtxid = "%s-%s-%s" % (
                self.channel.server.hash_id,
                self.channel.channel_number,
                self.request_count
            )
            self.ltxid = 1000
        else:
            self.ltxid = self.get_header ("X-Ltxn-Id")
            if not self.ltxid:
                raise ValueError ("Local txn ID missing")
            self.ltxid = int (self.ltxid) + 1000

        self.token = None
        self.claim = None
        self.user = None
        self.host = self.get_header ("host")
        self.user_agent = self.get_header ("user-agent")

    def get_gtxid (self):
        return self.gtxid

    def get_ltxid (self, delta = 1):
        self.ltxid += delta
        return str (self.ltxid)

    def get_scheme (self):
        return hasattr (self.channel.server, 'ctx') and "https" or "http"

    def get_raw_header (self):
        return self.header
    get_headers = get_raw_header

    path_regex = re.compile (r'([^;?#]*)(;[^?#]*)?(\?[^#]*)?(#.*)?')
    def split_uri (self):
        if self._split_uri is None:
            m = self.path_regex.match (self.uri)
            if m.end() != len(self.uri):
                raise ValueError("Broken URI")
            else:
                self._split_uri = m.groups()
        return self._split_uri

    def get_header_with_regex (self, head_reg, group):
        for line in self.header:
            m = head_reg.match (line)
            if m.end() == len(line):
                return head_reg.group (group)
        return ''

    def set_header (self, name, value):
        self.header.append ("%s: %s" % (name, value))

    def get_header (self, header = None, default = None):
        if header is None:
            return self.header
        header = header.lower()
        hc = self._header_cache
        if header not in hc:
            h = header + ':'
            hl = len(h)
            for line in self.header:
                if line [:hl].lower() == h:
                    r = line [hl:].strip ()
                    hc [header] = r
                    return r
            hc [header] = None
            return default
        else:
            return hc[header] is not None and hc[header] or default

    def get_header_params (self, header, default = None):
        v = self.get_header (header, default)
        if v is None:
            return default, {}
        return http_util.parse_params (v)

    get_header_with_attr = get_header_params

    def get_header_noparam (self, header, default = None):
        return self.get_header_params (header, default) [0]

    def get_charset (self):
        return self.get_attr ("content-type", "charset")

    def get_attr (self, header, attrname = None, default = None):
        value, attrs = self.get_header_params (header, None)
        if not value:
            return default
        if not attrname:
            return attrs
        return attrs.get (attrname, default)

    def get_content_length (self):
        try: return int (self.get_header ("content-length"))
        except: return None

    def get_content_type (self):
        return self.get_header_with_attr ("content-type") [0]

    def get_main_type (self):
        ct = self.get_content_type ()
        if ct is None:
            return
        return ct.split ("/", 1) [0]

    def get_sub_type (self):
        ct = self.get_content_type ()
        if ct is None:
            return
        return ct.split ("/", 1) [1]

    def get_user_agent (self):
        return self.get_header ("user-agent")

    def is_private_ip (self):
        ip = self.channel.addr [0]
        if ip [:8] in ("127.0.0.", "192.168."):
            return True
        if ip [:3] == "10.":
            return True
        if ip [:4] == "172."and 16 <= int (ip [4:].split (".", 1)[0]) < 32:
                return True

    def get_real_ip (self):
        ips = self.get_header ("X-Forwarded-For")
        if not ips:
            return self.channel.addr [0]
        return ips.split (",", 1)[0].strip ()

    def get_remote_addr (self):
        return self.channel.addr [0]

    def collect_incoming_data (self, data):
        if self.collector:
            self.rbytes += len (data)
            self.collector.collect_incoming_data (data)
        else:
            self.logger.log (
                'dropping %d bytes of incoming request data' % len(data),
                'warn'
                )

    def found_terminator (self):
        if self.collector:
            self.collector.found_terminator()
        else:
            self.logger.log (
                'unexpected end-of-record for incoming request',
                'warn'
                )

    def response_finished (self):
        if self.response:
            self.response.request = None

    def xmlrpc_serialized (self):
        # for compat with client request
        return self._xmlrpc_serialized
