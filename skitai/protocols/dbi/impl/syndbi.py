from ..dbconnect import DBConnect
from . import asynpsycopg2
import sqlite3
import threading

DEBUG = False

class OperationalError (Exception):
    pass


class SynConnect (asynpsycopg2._AsynConnect):
    def __init__ (self, address, params = None, lock = None, logger = None):
        DBConnect.__init__ (self, address, params, lock, logger)
        self.connected = False
        self.conn = None
        self.cur = None

    def close_if_over_keep_live (self):
        # doesn't need disconnect with local file
        pass

    def is_channel_in_map (self, map = None):
        return False

    def del_channel (self, map=None):
        pass

    def close (self):
        self.close_cursor ()
        if self.conn:
            self.conn.close ()
            self.conn = None
        self.connected = False
        DBConnect.close (self)

    def connect (self):
        try:
            self.conn = sqlite3.connect (self.address, check_same_thread = False, detect_types = sqlite3.PARSE_DECLTYPES)
        except:
            self.handle_error ()
        else:
            self.connected = True

    def set_auto_commit (self):
        self.conn.isolation_level = None

    def execute (self, request, *args, **kargs):
        DBConnect.begin_tran (self, request)
        sql = self._compile (request)

        if not self.connected:
            self.connect ()
            self.set_auto_commit ()

        try:
            if self.cur is None:
                self.cur = self.conn.cursor ()

            is_script = isinstance (request.params [0], (list, tuple))
            if not is_script and (len (request.params) > 1 or sql [:7].lower () == "select " or sql.lower ().find ('returning ') != -1):
                self.cur.execute (sql, *request.params [1:])
                self.has_result = True
            else:
                self.cur.executescript (sql)
        except:
            self.handle_error ()
        else:
            self.close_case (commit = True)


class Postgres (SynConnect):
    DEFAULT_PORT = 5432
    def get_host (self):
        if isinstance (self.address, tuple):
            return self.address
        return self.address, self.DEFAULT_PORT

    def connect (self):
        try:
            host, port = self.get_host ()
            self.conn = psycopg2.connect (
                dbname = self.dbname,
                user = self.user,
                password = self.password,
                host = host,
                port = port
            )
        except:
            self.handle_error ()
        else:
            self.connected = True

    def close_if_over_keep_live (self):
        DBConnect.close_if_over_keep_live (self)

    def execute (self, request, *args, **kargs):
        DBConnect.begin_tran (self, request)
        sql = self._compile (request)

        if not self.connected:
            self.connect ()
            self.set_auto_commit ()

        try:
            if self.cur is None:
                self.cur = self.conn.cursor ()
            sql = self._compile (request)
            self.cur.execute (sql, *request.params [1:])
            self.has_result = True
        except:
            self.handle_error ()
        else:
            self.close_case (commit = True)


class Oracle (Postgres):
    DEFAULT_PORT = 1521
    def connect (self):
        try:
            host, port = self.get_host ()
            self.conn = cx_Oracle.connect (
                user = self.user,
                password = self.password,
                dsn = f'{host}:{port}/{self.dbname}'
            )
        except:
            self.handle_error ()
        else:
            self.connected = True

    def set_auto_commit (self):
        self.conn.autocommit = True


class Redis (Postgres):
    DEFAULT_PORT = 6379
    def close (self):
        if self.conn:
            self.conn.close ()
            self.conn = None
        self.connected = False
        DBConnect.close (self)

    def close_case (self, commit = False):
        if self.request:
            self.request.handle_result (None, self.expt, self.fetchall ())
        DBConnect.close_case (self, commit)

    def connect (self):
        host, port = self.get_host ()
        self.conn = redis.Redis (host = host, port = port, db = self.dbname)

    def fetchall (self):
        result, self.response = self.response, None
        return result

    def prefetch (self):
        self.response = getattr (self.conn, self.request.method) (*self.request.params)
        self.has_result = True

    def execute (self, request, *args, **kargs):
        DBConnect.begin_tran (self, request)
        try:
            if not self.connected:
                self.connect ()
            self.prefetch ()
        except:
            self.handle_error ()
        else:
            self.close_case (commit = True)


class MongoDB (Redis):
    DEFAULT_PORT = 27017
    def prefetch (self):
        self.response = getattr (self.conn [self.request.dbname], self.request.method.lower ()) (*self.request.params)
        self.has_result = True

    def connect (self):
        user, password = "", ""
        auth = self.request.auth
        if auth:
            if len (auth) == 2:
                user, password = auth
            else:
                user = auth [0]

        host, port = self.get_host ()
        kargs = {}
        if user: kargs ["username"] = user
        if password: kargs ["password"] = password
        if port: kargs ["port"] = port
        self.conn = pymongo.MongoClient (host = host, **kargs)


from rs4.annotations import Uninstalled

try:
    import psycopg2
except ImportError:
    Postgres = Uninstalled ('psycopg2')

try:
    import cx_Oracle
except ImportError:
    Oracle = Uninstalled ('cx_Oracle')

try:
    import redis
except ImportError:
    Redis = Uninstalled ('redis')

try:
    import pymongo
except ImportError:
    MongoDB = Uninstalled ('pymongo')
