# testing purpose WAS sync service

from . import async_service
from ..rpc import cluster_dist_call
from ..dbi import cluster_dist_call as dcluster_dist_call 
from skitai import DB_SQLITE3, DB_PGSQL, DB_REDIS, DB_MONGODB
from rs4 import webtest
from rs4.cbutil import tuple_cb
import random
from urllib.parse import urlparse, urlunparse       
from skitai import exceptions
 
class Result:
    def __init__ (self, status, response = None):
        self.status = status
        self.__response = response
    
    def __getattr__ (self, attr):
        return getattr (self.__response, attr)
            
    @property
    def data (self):
        if hasattr (self.__response, "status_code"):                
            ct = self.__response.headers.get ("content-type", "")
            if ct:
                if ct.startswith ("application/json"):
                    return self.__response.json ()
            return self.__response.text
        return self.__response    
    
    def data_or_throw (self):
        return self.data
    
    def one_or_throw (self):
        try: 
            return self.data [0]
        except IndexError:
            raise exceptions.HTTPError ("404 Not Found")

class ProtoCall (cluster_dist_call.ClusterDistCall):
    def __init__ (self, cluster, *args, **kargs):
        self.cluster = cluster
        self.result = None        
        self.handle_request (*args, **kargs)       
            
    def  handle_request (self, uri, params = None, reqtype="rpc", headers = None, auth = None, meta = None, use_cache = True, mapreduce = False, filter = None, callback = None, timeout = 10, caller = None):
        self._mapreduce = mapreduce
        if self.cluster:
            endpoints = self.cluster.get_endpoints ()
            endpoint = random.choice (endpoints)
        else:
            parts = urlparse (uri)
            endpoint = "{}://{}".format (parts [0], parts [1])
            uri = urlunparse (("", "") + parts [2:]) 
                     
        with webtest.Target (endpoint) as cli:
            req_func = getattr (cli, reqtype)
            try:
                resp = req_func (uri, headers = headers, auth = auth)                                
            except:
                self.result = Result (1)
            else:
                self.result = Result (3, resp)        
        self.result.meta = meta or {}
        callback and callback (self.result)
    
    def set_callback (self, callback, reqid = None, timeout = 10):
        if reqid is not None:
            self.result.meta ["__reqid"] = reqid                        
        tuple_cb (self.result, callback)
        
    def wait (self):
        pass
    
    def _or_throw (self, func, timeout, cache):
        if self.result.status != 3:        
            raise exceptions.HTTPError ("502 Bad Gateway", sys.exc_info ())
        return self.result
            
    def dispatch (self):
        if self._mapreduce:
            self.result = cluster_dist_call.Results ([self.result])
        return self.result
    getwait = dispatch
    getswait = dispatch
        
    def data_or_throw (self, timeout = 10):
        return self.result.data_or_throw ()
        

class DBCall (ProtoCall):
    def __init__ (self, cluster, *args, **kargs):
        self.cluster = cluster
        self.result = None
        self.args, self.kargs = args, kargs
        try:
            from sqlalchemy.dialects import postgresql
        except ImportError:
            self.dialect = None
        else:
            self.dialect = postgresql.dialect ()
        
    def _compile (self, params):
        statement = params [0]
        if isinstance(statement, str):
            return params
        elif self.dialect:
            return (str (statement.compile (dialect = self.dialect, compile_kwargs = {"literal_binds": True})),)            
        else:
            raise ValueError ("SQL statement error")                
        return ""  
        
    def _build_request (self, method, param):
        self.handle_request (method, param, *self.args, **self.kargs)
        
    def  handle_request (self, method, param, server = None, dbname = None, auth = None, dbtype = None, meta = None, use_cache = True, mapreduce = False, filter = None, callback = None, timeout = 10, caller = None):
        from ..dbi import cluster_manager
        from ..dbi import endpoints
        
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
            raise
            self.result = Result (1)            
            self.result.status_code, self.result.reason = 500, "Exception Occured"            
        else:
            self.result = Result (3, resp)
            self.result.status_code, self.result.reason = 200, "OK"
            
        self.result.meta = meta or {}    
        endpoints.restore (conns)        
        callback and callback (self.result)
    
    def one_or_throw (self, timeout = 10):
        return self.result.one_or_throw ()    

class SyncService (async_service.AsyncService):
    def _create_rest_call (self, cluster, *args, **kargs):
        return ProtoCall (cluster, *args, **kargs)
    
    def _create_dbo (self, cluster, *args, **kargs):
        return dcluster_dist_call.Proxy (DBCall, cluster, *args, **kargs)
    
