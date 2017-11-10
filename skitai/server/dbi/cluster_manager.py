from skitai.server.rpc import cluster_manager
from aquests.dbapi import asynpsycopg2, synsqlite3, asynredis, asynmongo
from skitai import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB

class ClusterManager (cluster_manager.ClusterManager):
	backend_keep_alive = 1200
	backend = True
	
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
			if member.find ("@") != -1:
				auth, netloc = self.parse_member (member)
				try:
					server, db = netloc.split ("/", 1)
				except ValueError:
					server, db = netloc, ""
					
			else:				
				db, user, passwd = "", "", ""
				args = member.split ("/", 3)
				if len (args) == 4: 	server, db, user, passwd = args
				elif len (args) == 3: 	server, db, user = args
				elif len (args) == 2: 	server, db = args		
				else: server = args [0]
				auth = (user, passwd)
				
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
			
			asyncon = conn_class (server, (db, auth), self.lock, self.logger)	
			self.backend and asyncon.set_backend (self.backend_keep_alive)			
			nodeid = server
				
		return nodeid, asyncon # nodeid, asyncon

