from rs4 import attrdict
import time
import sys
import os
import json
from urllib.parse import urlparse, quote
from .hyper import HTTP20Connection

class HttpResponse:
    def __init__ (self, r, p):
        self.headers = self._rebuild_headers (r.headers)
        self.events = r.events
        self.status_code = r.status
        self.reason =  r.reason
        self.content = r.read ()
        self.promises = p

    def _rebuild_headers (self, headers):
        headers_ = attrdict.CaseInsensitiveDict ()
        for k, v in headers.items ():
            headers_ [k.decode ()] = v.decode ()
        return headers_

    @property
    def text (self):
        return self.content.decode ()

    def json (self):
        return json.loads (self.text)

    def get_pushes (self):
        return self.promises


class Session:
    def __init__ (self, endpoint):
        self.endpoint = endpoint
        parts = urlparse (self.endpoint)
        self.conn = HTTP20Connection (parts.netloc, enable_push = True, secure=parts.scheme == 'https')

    def urlencode (self, params, to_bytes = True):
        fm = []
        for k, v in list(params.items ()):
            fm.append ("%s=%s" % (quote (k), quote (str (v))))
        if to_bytes:
            return "&".join (fm).encode ("utf8")
        return "&".join (fm)

    def _rebuild_header (self, headers_, data):
        headers_ = headers_ or {}
        headers = attrdict.CaseInsensitiveDict ()
        for k, v in headers_.items ():
            headers [k] = v
        if data and headers.get ('content-type') is None:
            headers ['Content-Type'] = 'application/x-www-form-urlencoded'
        return headers

    def _request (self, method, urls, data = None, headers = {}):
        issingle = False
        if isinstance (urls, str):
            issingle = True
            urls = [urls]
        headers = self._rebuild_header (headers, data)
        if data and isinstance (data, dict):
            data = self.urlencode (data)
        stream_ids = [ self.conn.request (method.upper (), url, data, headers) for url in urls ]
        rs = []
        for stream_id in stream_ids:
            try:
                pushes = list (self.conn.get_pushes (stream_id))
            except:
                pushes = []
            r = HttpResponse (self.conn.get_response(stream_id), pushes)
            rs.append (r)
        return rs [0] if issingle else rs

    def get (self, urls, headers = {}):
        return self._request ('GET', urls, headers = headers)

    def delete (self, urls, headers = {}):
        return self._request ('DELETE', urls, headers = headers)

    def options (self, urls, headers = {}):
        return self._request ('OPTIONS', urls, headers = headers)

    def head (self, urls, headers = {}):
        return self._request ('HEAD', urls, headers = headers)

    def post (self, urls, data, headers = {}):
        return self._request ('POST', urls, data, headers)

    def put (self, urls, data, headers = {}):
        return self._request ('PUT', urls, data, headers)

    def patch (self, urls, data, headers = {}):
        return self._request ('PATCH', urls, data, headers)

