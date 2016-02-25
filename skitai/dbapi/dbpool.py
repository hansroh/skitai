import threading
import time
from . import asynpsycopg2
from . import synsqlite3
from skitai.client import socketpool
from skitai import DB_PGSQL, DB_SQLITE3

class DBPool (socketpool.SocketPool):
	object_timeout = 300
	
	def get_name (self):
		return "__dbpool__"
			
	def create_asyncon (self, server, params, dbtype):
		if DB_SQLITE3 in (params [0], dbtype):
			return synsqlite3.SynConnect (server, params, self.lock, self.logger)
		
		if dbtype == DB_PGSQL:
			try: 
				host, port = server.split (":", 1)
			except ValueError:
				host, port = server, 5432
			return asynpsycopg2.AsynConnect ((host, port), params, self.lock, self.logger)		
						
	def get (self, server, dbname, user, pwd, dbtype = DB_PGSQL):
		serverkey = "%s/%s/%s/%s" % (server, dbname, user, dbtype)
		return self._get (serverkey, server, (dbname, user, pwd), dbtype)


if __name__ == "__main__":
	from skitai import lifetime
	from skitai.lib import logger
	from skitai.server.threads import trigger
	
	trigger.start_trigger ()
	pool = DBPool (logger.screen_logger ())
	
	def query ():
		conn = pool.get ("mydb.us-east-1.rds.amazonaws.com:5432", "mydb", "postgres", "")
		conn.execute ("SELECT * FROM cities;")
		rs = conn.fetchwait (5)
		print(rs.status, rs.result)
		
		conn.execute ("INSERT INTO weather VALUES ('San Francisco', 46, 50, 0.25, '1994-11-27');")		
		rs = conn.wait (5)
		print(rs.status, rs.result)
		
		conn.execute ("INSERT INTO weather VALUES ('San Francisco', 54, 67, 0.25, '1994-11-27');")		
		rs = conn.wait (5)
		print(rs.status, rs.result)
		
		
	threading.Thread (target = query).start ()	
	while threading.activeCount () > 1:
		lifetime.loop ()
		