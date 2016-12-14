from skitai.server.rpc import cluster_manager
from skitai.dbapi import asynpsycopg2, synsqlite3
from skitai import DB_PGSQL, DB_SQLITE3

class ClusterManager (cluster_manager.ClusterManager):
	object_timeout = 1200	
	maintern_interval = 60
	
	def __init__ (self, name, cluster, dbtype = DB_PGSQL, logger = None):
		self.dbtype = dbtype
		cluster_manager.ClusterManager.__init__ (self, name, cluster, 0, logger)
			
	def match (self, request):
		return False # not serverd by url
	
	def create_asyncon (self, member):
		if self.dbtype == DB_PGSQL:
			try:
				server, db, user, passwd = member.split ("/", 3)
			except:
				server, db, user, passwd = member, "", "", ""				
			try: 
				host, port = server.split (":", 1)
				server = (host, int (port))
			except ValueError: 
				server	= (server, 5432)				
			asyncon = asynpsycopg2.AsynConnect (server, (db, user, passwd), self.lock, self.logger)
			nodeid = server
		
		elif self.dbtype == DB_SQLITE3:
			asyncon = synsqlite3.SynConnect (member, None, self.lock, self.logger)
			nodeid = member
			
		return nodeid, asyncon # nodeid, asyncon

