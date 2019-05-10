from ..rpc import cluster_manager
from aquests.dbapi import asynpsycopg2, synsqlite3, asynredis, asynmongo
from skitai import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB
from . import endpoints
from sqlphile import pg2
from sqlphile import db3
            
class ClusterManager (cluster_manager.ClusterManager):
    backend_keep_alive = 1200
    backend = True
    
    def __init__ (self, name, cluster, dbtype = DB_PGSQL, access = [], max_conns = 200, logger = None):
        self.dbtype = dbtype
        self._cache = []
        cluster_manager.ClusterManager.__init__ (self, name, cluster, 0, access, max_conns, logger)
            
    def match (self, request):
        return False # not serverd by url
    
    def create_asyncon (self, member):        
        if self.dbtype == DB_SQLITE3:
            asyncon = synsqlite3.SynConnect (member, None, self.lock, self.logger)
            nodeid = member
            self._cache.append (((member, 0), "", ("", "")))
        
        else:
            if member.find ("@") != -1:
                auth, netloc = self.parse_member (member)
                try:
                    server, db = netloc.split ("/", 1)
                except ValueError:
                    server, db = netloc, ""
                    
            else:                
                db, user, passwd = "", "", ""
                args = member.split ("/", 3)
                if len (args) == 4:     server, db, user, passwd = args
                elif len (args) == 3:     server, db, user = args
                elif len (args) == 2:     server, db = args        
                else: server = args [0]
                auth = (user, passwd)
                
            try: 
                host, port = server.split (":", 1)
                server = (host, int (port))
            except ValueError: 
                server = (server, 5432)
            
            if self.dbtype == DB_PGSQL:
                conn_class = asynpsycopg2.AsynConnect
            elif self.dbtype == DB_REDIS:
                conn_class = asynredis.AsynConnect
            elif self.dbtype == DB_MONGODB:
                conn_class = asynmongo.AsynConnect    
            else:
                raise TypeError ("Unknown DB type: %s" % self.dbtype)
            
            asyncon = conn_class (server, (db, auth), self.lock, self.logger)    
            self.backend and asyncon.set_backend (self.backend_keep_alive)            
            nodeid = server
            self._cache.append ((server, db, auth))
                
        return nodeid, asyncon # nodeid, asyncon
    
    def get_endpoints (self):
        return endpoints.make_endpoints (self.dbtype, self._cache)
    
    def getconn (self, auto_putback = True):
        if self.dbtype == DB_PGSQL:
            conn = endpoints.make_endpoints (self.dbtype, [self._cache [0]]) [0]
            return pg2.open2 (conn, endpoints.PGPOOL, auto_putback = auto_putback)
        elif self.dbtype == DB_SQLITE3:            
            conn = endpoints.make_endpoints (self.dbtype, [self._cache [0]]) [0]
            return db3.open2 (conn)
        raise TypeError ("Only DB_PGSQL or DB_SQLITE3")

