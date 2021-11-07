import sqlite3
from . import dbconnect, asynpsycopg2
import threading

DEBUG = False

class OperationalError (Exception):
    pass

class SynConnect (asynpsycopg2._AsynConnect):
    def __init__ (self, address, params = None, lock = None, logger = None):
        dbconnect.DBConnect.__init__ (self, address, params, lock, logger)
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
        dbconnect.DBConnect.close (self)

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
        dbconnect.DBConnect.begin_tran (self, request)
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
