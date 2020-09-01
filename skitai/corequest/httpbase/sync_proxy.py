# testing purpose WAS sync service

from . import task
from .. import corequest
from rs4.webkit import webtest
from rs4.cbutil import tuple_cb
import random
from urllib.parse import urlparse, urlunparse
from skitai import exceptions
import xmlrpc.client
import sys
from aquests.client import synconnect

class RPCResponse:
    def __init__ (self, val):
        self.data = val

class XMLRPCServerProxy (xmlrpc.client.ServerProxy):
     def _ServerProxy__request (self, methodname, params):
        response = xmlrpc.client.ServerProxy._ServerProxy__request (self, methodname, params)
        return Result (3, RPCResponse (response))

try:
    import jsonrpclib
except ImportError:
    pass
else:
    class JSONRPCServerProxy (jsonrpclib.ServerProxy):
         def _ServerProxy__request (self, methodname, params):
            response = xjsonrpclib.ServerProxy._ServerProxy__request (self, methodname, params)
            return Result (3, RPCResponse (response))

class Stub (webtest.Stub):
    def __init__ (self, cli, baseurl, headers, auth, meta, filter, callback):
        super ().__init__ (cli, baseurl, headers, auth)
        self._meta, self._filter, self._callback = meta, filter, callback

    def handle_request (self, uri, data):
        return Result (3, super ().handle_request (uri, data), None, self._meta, self._filter, self._callback)


class Result (corequest):
    def __init__ (self, status, response = None, expt = None, meta = {}, filter = None, callback = None):
        self.status = status
        self.__response = response
        self.__expt = expt
        self.meta = meta
        self.data = self.parse_response ()
        filter and filter (self)
        callback and self.set_callback (callback)

    def __getattr__ (self, attr):
        return getattr (self.__response, attr)

    def parse_response (self):
        if isinstance (self.__response, RPCResponse):
            return self.__response.data
        elif hasattr (self.__response, "status_code"):
            ct = self.__response.headers.get ("content-type", "")
            if ct:
                if ct.startswith ("application/json"):
                    return self.__response.json ()
            return self.__response.text
        return self.__response

    def set_callback (self, callback, reqid = None, timeout = 10):
        if reqid is not None:
            self.meta ["__reqid"] = reqid
        tuple_cb (self, callback)

    def reraise (self):
        if self.status !=3 and self.__expt:
            raise self.__expt [1]

    def fetch (self, *args, **kargs):
        self.reraise ()
        return self.data

    def one (self, *args, **kargs):
        self.reraise ()
        if not self.data:
            raise exceptions.HTTPError ("410 Maybe Gone")
        elif len (self.data) != 1:
            raise exceptions.HTTPError ("409 Conflict")
        return self.data [0]


class ProtoCall (task.Task):
    def __init__ (self, cluster, *args, **kargs):
        self.cluster = cluster
        self.result = None
        self.expt = None
        self._timeout = 10
        self.handle_request (*args, **kargs)

    def get_syncon (self, uri):
        if self.cluster:
            syncon = self.cluster.get ()
        else:
            parts = urlparse (uri)
            try:
                host, port = parts [1].split (":")
            except ValueError:
                port = parts [0] == "http" and 80 or 443
                host = parts [1]
            else:
                port = int (port)
            if parts [0] == "http":
                syncon = synconnect.SynConnect ((host, port))
            else:
                syncon = synconnect.SynSSLConnect ((host, port))
            uri = urlunparse (("", "") + parts [2:])
        syncon.connect ()
        return syncon, uri

    def create_stub (self, headers = None, auth = None, meta = None):
        syncon, uri = self.get_syncon (self.uri)
        with syncon.webtest as cli:
            if self.reqtype == "stub":
                return Stub (cli.axios, uri, self.headers, self.auth, self.meta, self.filter, self.callback)

            if self.reqtype == "jsonrpc":
                proxy_class = JSONRPCServerProxy
            else:
                proxy_class = XMLRPCServerProxy
            return getattr (cli, self.reqtype) (uri, proxy_class)

    def handle_request (self, uri, params = None, reqtype="rpc", headers = None, auth = None, meta = None, use_cache = True, mapreduce = False, filter = None, callback = None, cache = None, timeout = 10, caller = None):
        self._mapreduce = mapreduce
        self._meta = meta
        self.uri = uri
        self.reqtype = reqtype
        self.headers, self.auth, self.meta, self.filter, self.callback = headers, auth, meta, filter, callback

        if reqtype.endswith ('rpc') or reqtype.endswith ('stub'):
            return

        syncon, uri = self.get_syncon (uri)
        syncon.set_auth (auth)
        with syncon.webtest as cli:
            req_func = getattr (cli, reqtype)
            try:
                resp = req_func (uri, headers = headers, auth = auth)
            except:
                self.expt = sys.exc_info ()
                self.result = Result (1, expt = self.expt, filter = filter, meta = meta, callback = callback)
            else:
                self.result = Result (3, resp, meta = meta, callback = callback)
            syncon.set_active (False)

    def set_callback (self, callback, reqid = None, timeout = 10):
        if reqid is not None:
            self.result.meta ["__reqid"] = reqid
        tuple_cb (self.result, callback)

    def wait (self, timeout = 10, *args, **karg):
        pass

    def _or_throw (self):
        if self.expt:
            raise exceptions.HTTPError ("700 Exception", self.expt)
        if self.result.status_code >= 300:
            raise exceptions.HTTPError ("{} {}".format (self.result.status_code, self.result.reason))
        return self.result

    def dispatch (self, *args, **kargs):
        if self._mapreduce:
            self.result = task.Results ([self.result])
        return self.result
    getwait = dispatch
    getswait = dispatch

    def dispatch_or_throw (self):
        self.dispatch ()
        return self._or_throw ()

    def commit (self, *args, **karg):
        return self._or_throw ()
    wait_or_throw = commit

    def fetch (self, timeout = 10, *args, **karg):
        self._or_throw ()
        return self.result.fetch ()

    def one (self, timeout = 10, *args, **karg):
        self._or_throw ()
        return self.result.one ()
