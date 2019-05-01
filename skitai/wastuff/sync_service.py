# testing purpose WAS sync service

from . import async_service
from ..coops.rpc import cluster_dist_call
from ..coops.dbi import cluster_dist_call as dcluster_dist_call 
from skitai import DB_SQLITE3, DB_PGSQL, DB_REDIS, DB_MONGODB
from rs4 import webtest
from rs4.cbutil import tuple_cb
import random
from urllib.parse import urlparse, urlunparse       
from skitai import exceptions
import xmlrpc.client
import sys

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
     
class Result:
    def __init__ (self, status, response = None):
        self.status = status
        self.__response = response
    
    def __getattr__ (self, attr):
        return getattr (self.__response, attr)
            
    @property
    def data (self):
        if isinstance (self.__response, RPCResponse):
            return self.__response.data        
        elif hasattr (self.__response, "status_code"):                
            ct = self.__response.headers.get ("content-type", "")
            if ct:
                if ct.startswith ("application/json"):
                    return self.__response.json ()
            return self.__response.text
        return self.__response    
    
    def reraise (self):
        if self.status !=3 and self.__response:            
            raise self.__response [1]

    def fetch (self, *args, **kargs):
        self.reraise ()
        return self.data
    
    def one (self, *args, **kargs):
        self.reraise ()
        if not self.data:
            raise exceptions.HTTPError ("404 Not Found")
        elif len (self.data) != 1:
            raise exceptions.HTTPError ("409 Conflict")
        return self.data [0]
            

class ProtoCall (cluster_dist_call.ClusterDistCall):
    def __init__ (self, cluster, *args, **kargs):
        self.cluster = cluster
        self.result = None        
        self.expt = None
        self.handle_request (*args, **kargs)       
    
    def get_endpoint (self, uri):
        if self.cluster:
            endpoints = self.cluster.get_endpoints ()
            endpoint = random.choice (endpoints)
        else:
            parts = urlparse (uri)
            endpoint = "{}://{}".format (parts [0], parts [1])
            uri = urlunparse (("", "") + parts [2:])
        return endpoint, uri     
            
    def create_stub (self):
        endpoint, uri = self.get_endpoint (self.uri)
        with webtest.Target (endpoint) as cli:
            if self.reqtype == "jsonrpc":
                proxy_class = JSONRPCServerProxy
            else:
                proxy_class = XMLRPCServerProxy
            return getattr (cli, self.reqtype) (endpoint, proxy_class)
                
    def  handle_request (self, uri, params = None, reqtype="rpc", headers = None, auth = None, meta = None, use_cache = True, mapreduce = False, filter = None, callback = None, timeout = 10, caller = None):
        self._mapreduce = mapreduce
        self.uri = uri
        self.reqtype = reqtype
        
        endpoint, uri = self.get_endpoint (uri)                             
        with webtest.Target (endpoint) as cli:
            req_func = getattr (cli, reqtype)
            try:
                resp = req_func (uri, headers = headers, auth = auth)                                
            except:
                self.expt = sys.exc_info ()
                self.result = Result (1, self.expt)
            else:
                self.result = Result (3, resp)        
        self.result.meta = meta or {}
        callback and callback (self.result)
    
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
            self.result = cluster_dist_call.Results ([self.result])
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
    
class DBCall (ProtoCall):
    def __init__ (self, cluster, *args, **kargs):
        self.cluster = cluster
        self.result = None
        self.args, self.kargs = args, kargs
        self.expt = None        

    def _or_throw (self):
        if self.expt:
            raise self.expt [1]
        return self.result

    def _compile (self, params):
        statement = params [0]
        if isinstance(statement, str):
            return params        
        else:
            raise ValueError ("SQL statement error")                
        return ""
        
    def _build_request (self, method, param):
        self.handle_request (method, param, *self.args, **self.kargs)
        
    def  handle_request (self, method, param, server = None, dbname = None, auth = None, dbtype = None, meta = None, use_cache = True, mapreduce = False, filter = None, callback = None, timeout = 10, caller = None):
        from ..coops.dbi import cluster_manager
        from ..coops.dbi import endpoints
        
        self._mapreduce = mapreduce
        
        assert dbtype is None, "please, alias {}".format (server)
        if self.cluster:
            conns = self.cluster.get_endpoints ()
        else:            
            conns = endpoints.make_endpoints (dbtype, [server, dbname, auth])
        conn = random.choice (conns)
        try:
            if self.cluster.dbtype in (DB_SQLITE3, DB_PGSQL):        
                stmt = self._compile (param)
                cur = conn.cursor ()
                getattr (cur, method) (*stmt)
                resp = cur.fetchall ()
                cur.close ()
            else:
                resp = getattr (conn, method) (*param)
        except:
            self.expt = sys.exc_info ()
            self.result = Result (1,  self.expt)            
            self.result.status_code, self.result.reason = 500, "Exception Occured"            
        else:
            self.result = Result (3, resp)
            self.result.status_code, self.result.reason = 200, "OK"
            
        self.result.meta = meta or {}    
        endpoints.restore (conns)        
        callback and callback (self.result)


class SyncService (async_service.AsyncService):
    def _create_rest_call (self, cluster, *args, **kargs):
        if args [2].endswith ("rpc"):            
            return ProtoCall (cluster, *args, **kargs).create_stub ()
        else:    
            return ProtoCall (cluster, *args, **kargs)
    
    def _create_dbo (self, cluster, *args, **kargs):
        return dcluster_dist_call.Proxy (DBCall, cluster, *args, **kargs)
    
