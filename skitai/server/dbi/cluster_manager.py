from skitai.server.rpc import cluster_manager
from skitai.dbapi import asynpsycopg2, synsqlite3, asynredis, asynmongo
from skitai import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB

class ClusterManager (cluster_manager.ClusterManager):	
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
			db, user, passwd = "", "", ""
			args = member.split ("/", 3)
			if len (args) == 4: 	server, db, user, passwd = args
			elif len (args) == 3: 	server, db, user = args	
			elif len (args) == 2: 	server, db = args		
			else: 					server = args [0]
			
			try: 
				host, port = server.split (":", 1)
				server = (host, int (port))
			except ValueError: 
				server	= (server, 5432)
			
			if self.dbtype == DB_PGSQL:
				conn_class = asynpsycopg2.AsynConnect
			elif self.dbtype == DB_REDIS:
				conn_class = asynredis.AsynConnect
			elif self.dbtype == DB_MONGODB:
				conn_class = asynmongo.AsynConnect	
			else:
				raise TypeError ("Unknown DB type: %s" % self.dbtype)
			
			asyncon = conn_class (server, (db, user, passwd), self.lock, self.logger)	
			nodeid = server
				
		return nodeid, asyncon # nodeid, asyncon

