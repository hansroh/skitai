from skitai.server.rpc import cluster_manager
from skitai.dbapi import asynpsycopg2, synsqlite3, asynredis
from skitai import DB_PGSQL, DB_SQLITE3, DB_REDIS

class ClusterManager (cluster_manager.ClusterManager):
	object_timeout = 1200	
	maintern_interval = 60
	
	def __init__ (self, name, cluster, dbtype = DB_PGSQL, access = [], logger = None):
		self.dbtype = dbtype
		cluster_manager.ClusterManager.__init__ (self, name, cluster, 0, access, logger)
			
	def match (self, request):
		return False # not serverd by url
	
	def create_asyncon (self, member):
		if self.dbtype == DB_SQLITE3:
			asyncon = synsqlite3.SynConnect (member, None, self.lock, self.logger)
			nodeid = member
		
		else:	
			try:
				server, db, user, passwd = member.split ("/", 3)
			except:
				server, db, user, passwd = member, "", "", ""

			try: 
				host, port = server.split (":", 1)
				server = (host, int (port))
			except ValueError: 
				server	= (server, 5432)
			
			if self.dbtype == DB_PGSQL:		
				conn_class = asynpsycopg2.AsynConnect
			elif self.dbtype == DB_REDIS:
				conn_class = asynredis.AsynConnect
			else:
				raise TypeError ("Unknown DB type: %s" % self.dbtype)
			
			asyncon = conn_class (server, (db, user, passwd), self.lock, self.logger)	
			nodeid = server
				
		return nodeid, asyncon # nodeid, asyncon

