from ..httpbase import cluster_manager
from aquests.dbapi import asynpsycopg2, synsqlite3, asynredis, asynmongo, syndbi, dbpool
from skitai import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB, DB_SYN_PGSQL, DB_SYN_REDIS, DB_SYN_MONGODB
from . import endpoints
from sqlphile import pg2, db3
from aquests.dbapi.dbconnect import ConnectProxy

class ClusterManager (cluster_manager.ClusterManager):
    backend_keep_alive = 10
    backend = True
    class_map = dbpool.DBPool.class_map
    proxy_class = ConnectProxy

    def __init__ (self, name, cluster, dbtype = DB_PGSQL, access = [], max_conns = 200, logger = None):
        self.dbtype = dbtype
        self._cache = []
        cluster_manager.ClusterManager.__init__ (self, name, cluster, 0, access, max_conns, logger)

    @classmethod
    def add_class (cls, name, class_):
        cls.class_map [name] = class_

    def match (self, request):
        return False # not serverd by url

    def create_asyncon (self, member):
        if self.dbtype == DB_SQLITE3:
            asyncon = self.class_map [DB_SQLITE3] (member, None, self.lock, self.logger)
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

            try:
                conn_class = self.class_map [self.dbtype]
            except KeyError:
                raise TypeError ("Unknown DB type: %s" % self.dbtype)

            asyncon = conn_class (server, (db, auth), self.lock, self.logger)
            self.backend and asyncon.set_backend (self.backend_keep_alive)
            nodeid = server
            self._cache.append ((server, db, auth))

        return nodeid, asyncon # nodeid, asyncon

    def get_endpoints (self):
        return endpoints.make_endpoints (self.dbtype, self._cache)

    def _openv (self, wrap):
        # transaction mode
        if self.dbtype in (DB_PGSQL, DB_SYN_PGSQL):
            conn = endpoints.make_endpoints (self.dbtype, [self._cache [0]]) [0]
            if wrap == "open2":
                return pg2.open2 (conn)
            return pg2.open3 (conn)
        elif self.dbtype == DB_SQLITE3:
            conn = endpoints.make_endpoints (self.dbtype, [self._cache [0]]) [0]
            if wrap == "open2":
                return db3.open2 (conn)
            return db3.open3 (conn)
        raise TypeError ("Only DB_PGSQL or DB_SQLITE3")

    def open2 (self):
        # single conn, single cursor
        return self._openv ('open2')

    def open3 (self):
        # single connection, multi cursors
        # it is replacable with was.db
        return self._openv ('open3')