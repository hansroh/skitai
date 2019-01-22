from .. import wsgiappservice
from ..rpc import cluster_dist_call
from ..dbi import cluster_dist_call as dcluster_dist_call 
from skitai import DB_SQLITE3, DB_PGSQL, DB_REDIS, DB_MONGODB
from rs4 import webtest
import random
from urllib.parse import urlparse, urlunparse       

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
    
class ProtoCall (cluster_dist_call.ClusterDistCall):
    def __init__ (self, cluster, *args, **kargs):
        self.cluster = cluster
        self.result = None   
        self.handle_request (*args, **kargs)       
            
    def  handle_request (self, uri, params = None, reqtype="rpc", headers = None, auth = None, meta = None, use_cache = True, mapreduce = False, filter = None, callback = None, timeout = 10, caller = None):
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
        callback and callback (self.result)
    
    def wait (self):
        pass
    
    def _or_throw (self, func, status, timeout, cache):
        if self.result.status != 3:        
            raise exceptions.HTTPError (status, sys.exc_info ())
        return self.result
            
    def getwait (self):
        return self.result
    
    def getswait (self):
        return cluster_dist_call.Results ([self.result])
        

class DBCall (ProtoCall):
    def __init__ (self, cluster, *args, **kargs):
        self.cluster = cluster
        self.result = None
        self.args, self.kargs = args, kargs
    
    def _request (self, method, param):
        self.handle_request (method, param, *self.args, **self.kargs)
        
    def  handle_request (self, method, param, server = None, dbname = None, auth = None, dbtype = None, meta = None, use_cache = True, mapreduce = False, filter = None, callback = None, timeout = 10, caller = None):
        from ..dbi import cluster_manager
        
        assert dbtype is None, "please, alias {}".format (server)
        if self.cluster:
            conns = self.cluster.get_endpoints ()
        else:            
            conns = cluster_manager.make_endpoints (dbtype, [server, dbname, auth])            
        conn = random.choice (conns)
        try:
            if self.cluster.dbtype in (DB_SQLITE3, DB_PGSQL):        
                cur = conn.cursor ()
                getattr (cur, method) (*param)
                resp = cur.fetchall ()
            else:
                resp = getattr (conn, method) (*param)
        except:
            self.result = Result (1)
        else:
            self.result = Result (3, resp)                    
        for conn in conns:
            conn.close ()
        callback and callback (self.result)
        
        
class WAS (wsgiappservice.WAS):
    def _create_rest_call (self, cluster, *args, **kargs):
        return ProtoCall (cluster, *args, **kargs)
    
    def _create_dbo (self, cluster, *args, **kargs):
        return dcluster_dist_call.Proxy (DBCall, cluster, *args, **kargs)
    
    