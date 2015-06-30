from skitai.server.rpc import cluster_manager
from skitai.dbapi import asynpsycopg2

class ClusterManager (cluster_manager.ClusterManager):
	object_timeout = 1200
	
	def match (self, request):
		return False # not serverd by url
		
	def set_ssl (self, flag):
		self._use_ssl = flag
		self._conn_class = asynpsycopg2.AsynConnect
	
	def create_asyncon (self, member):
		try:
			server, db, user, passwd = member.split ("/", 3)
		except:
			server, db, user, passwd = member, "", "", ""
			
		try: 
			host, port = server.split (":", 1)
			server = (host, int (port))
		except ValueError: 
			server	= (server, 5432)
					
		asyncon = self._conn_class (server, db, user, passwd, self.lock, self.logger)

		return server, asyncon # nodeid, asyncon
