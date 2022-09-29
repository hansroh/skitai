from rs4.protocols.sock.impl.http import request
from rs4.protocols.sock.impl.grpc import request as grpc_request
from rs4.protocols.sock.impl.ws import request as ws_request
from ...backbone.http_request import http_request
from base64 import b64encode
import os
from .server import Channel, get_client_response
from rs4.webkit import siesta
from urllib.parse import urlparse

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.8,en-US;q=0.6,en;q=0.4",
    "Referer": "https://pypi.python.org/pypi/skitai",
    "Upgrade-Insecure-Requests": 1,
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
    "Host": "skitai.com"
}

class Method (siesta.Resource):
    ACCPET = "*/*"
    def __call__(self, *args):
        script = urlparse (self._api._base_url) [2]
        method = self._url [len (script):]
        return self._callback (self._api._base_url, method.replace ("/", "."), args)

class RPC (siesta.API):
    RESOURCE_CLASS = Method
    def __call__(self):
        raise AttributeError

class Client:
    def override (self, headers):
        copied = DEFAULT_HEADERS.copy ()
        for k, v in headers:
            copied [k] = v
        return copied

    def handle_request (self, request, handler = None):
        # clinet request -> process -> server response -> client response
        return get_client_response (request, handler)

    def __serialize (self, payload):
        _payload = []
        while 1:
            d = payload.more ()
            if not d: break
            _payload.append (d)
        return b"".join (_payload)

    def __generate (self, r):
        m, u, v = r.get_method (), r.path, r.http_version
        headers = ["%s: %s" % each for each in r.get_headers ()]
        return http_request (Channel (), "%s %s HTTP/%s" % (m, u, v), m.lower (), u, v, headers)

    def make_request (self, method, uri, data, headers, auth = None, meta = {}, version = "1.1"):
        method = method.upper ()
        if isinstance (headers, dict):
            headers = [(k, v) for k, v in headers.items ()]
        headers = self.override (headers)
        if method == "UPLOAD":
            r = request.HTTPMultipartRequest (uri, "POST", data, headers, auth, None, meta, version)
        else:
            r = request.HTTPRequest (uri, method, data, headers, auth, None, meta, version)
        hr = self.__generate (r)
        if data:
            payload = r.get_payload ()
            if method == "UPLOAD":
                payload = self.__serialize (payload)
            hr.set_body (payload)
        return hr

    def get (self, uri, headers = [], auth = None, meta = {}, version = "1.1"):
        return self.make_request ("GET", uri, None, headers, auth, meta, version)

    def delete (self, uri, headers = [], auth = None, meta = {}, version = "1.1"):
        return self.make_request ("DELETE", uri, None, headers, auth, meta, version)

    def post (self, uri, data, headers = [], auth = None, meta = {}, version = "1.1"):
        return self.make_request ("POST", uri, data, headers, auth, meta, version)

    def postjson (self, uri, data, headers = [], auth = None, meta = {}, version = "1.1"):
        headers.append (('Accpet', 'application/json'))
        headers.append (('Content-Type', 'application/json'))
        return self.make_request ("POST", uri, data, headers, auth, meta, version)

    def patch (self, uri, data, headers = [], auth = None, meta = {}, version = "1.1"):
        return self.make_request ("PATCH", uri, data, headers, auth, meta, version)

    def put (self, uri, data, headers = [], auth = None, meta = {}, version = "1.1"):
        return self.make_request ("PUT", uri, data, headers, auth, meta, version)

    def upload (self, uri, data, headers = [], auth = None, meta = {}, version = "1.1"):
        return self.make_request ("UPLOAD", uri, data, headers, auth, meta, version)

    def ensure_directory (self, url):
        if not url:
            url = "/"
        elif url [-1] != "/":
            url += "/"
        return url

    # api ----------------------------------------------------
    def api (self, endpoint = ""):
        return siesta.API (endpoint, callback = self.make_request)

    # rpc ----------------------------------------------------
    def rpc (self, endpoint = ""):
        return RPC (endpoint, callback = self.__continue_xmlrpc)
    xmlrpc = rpc

    def rpc_request (self, endpoint = ""):
        return RPC (endpoint, callback = self.__get_rpc_request)
    xmlrpc_request = rpc_request

    def __get_rpc_request (self, uri, method, data, headers = [], auth = None, meta = {}, version = "2.0"):
        r = request.XMLRPCRequest (self.ensure_directory (uri), method, data, self.override (headers), auth, None, meta, version)
        hr = self.__generate (r)
        hr.set_body (r.get_payload ())
        hr._xmlrpc_serialized = True
        return hr

    def __continue_xmlrpc (self, *args, **kargs):
        hr = self.__get_rpc_request (*args, **kargs)
        resp = self.handle_request (hr)
        return resp.data

    # jsonrpc
    def jsonrpc (self, endpoint = ""):
        return RPC (endpoint, callback = self.__continue_jsonrpc)

    def jsonrpc_request (self, endpoint = ""):
        return RPC (endpoint, callback = self.__get_jsonrpc_request)

    def __get_jsonrpc_request (self, uri, method, data, headers = [], auth = None, meta = {}, version = "1.1"):
        r = request.JSONRPCRequest (self.ensure_directory (uri), method, data, self.override (headers), auth, None, meta, version)
        hr = self.__generate (r)
        hr.set_body (r.get_payload ())
        return hr

    def __continue_jsonrpc (self, *args, **kargs):
        hr = self.__get_jsonrpc_request (*args, **kargs)
        resp = self.handle_request (hr)
        return resp.data

    # grpc
    def grpc (self, endpoint = ""):
        raise NotImplementedError
        return RPC (endpoint, callback = self.__continue_grpc)

    def __get_grpc_request (self, uri, method, data, headers = [], auth = None, meta = {}, version = "2.0"):
        r = grpc_request.GRPCRequest (uri, method, data, self.override (headers), auth, None, meta, version)
        hr = self.__generate (r)
        hr.set_body (self.__serialize (r.get_payload ()))
        return hr

    def __continue_grpc (self, *args, **kargs):
        hr = self.__get_grpc_request (*args, **kargs)
        resp = self.handle_request (hr)
        return resp.data

    def grpc_request (self, endpoint = ""):
        return RPC (endpoint, callback = self.__get_grpc_request)

    # websokcet --------------------------------------------
    def ws (self, uri, message, headers = [], auth = None, meta = {}, version = "1.1"):
        r = ws_request.Request (uri, message, self.override (headers), auth, None, meta, version)
        origin = r.address or ("127.0.0.1", 80)
        r.headers ['Origin'] = "http://%s:%d" % origin
        r.headers ['Sec-WebSocket-Key'] = b64encode(os.urandom(16))
        r.headers ['Connection'] = "keep-alive, Upgrade"
        r.headers ['Upgrade'] = 'websocket'
        r.headers ['Cache-Control'] = 'no-cache'
        r.method = "get"
        hr = self.__generate (r)
        hr.set_body (r.get_payload ().more ())
        return self.handle_request (hr)
