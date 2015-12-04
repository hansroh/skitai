from . import ssgi_handler, proxy_handler
from skitai.protocol.http import request as http_request
import re
	
class Handler (proxy_handler.Handler):
	def match (self, request):
		if self.find_cluster (request):
			return 1
		else:
			return 0
			
	def find_cluster (self, request):
		for cluster in list(self.clusters.values ()):
			if cluster.match (request):
				return cluster
						
	def continue_request (self, request, collector):
		request.loadbalance_retry = 0
		if self.is_cached (request, collector is not None):
			return
		
		try:
			self.route (request, collector)			
		except:
			self.wasc.logger.trace ("server")	
			request.response.error (500, ssgi_handler.catch (1))
	
	def route (self, request, collector):
		current_cluster = self.find_cluster (request)
		maybe_route = current_cluster.get_route_index (request)
		if maybe_route: 
			route = int (maybe_route)			
		else:
			route = -1
				
		psysicaluri = request.uri [len (maybe_route) + current_cluster.get_path_length ():]
		if psysicaluri == "": psysicaluri = "/"
		elif psysicaluri[0] != "/": psysicaluri = "/" + psysicaluri
		
		request.loadbalance_retry += 1
		asyncon = current_cluster.get (index = route)
		
		if not asyncon: 
			request.logger ("no available socket in cluster pool, retry: %d, url: %s, cluster index: %d" % (
				request.loadbalance_retry, 
				request.uri, 
				route
				), 'warn')
			return request.response.error (503)
		
		if request.loadbalance_retry > 1:
			request.logger ("route call multiple retry, retry: %d, server: %s:%s (connected:%s), url: %s, cluster index: %d" % (
				request.loadbalance_retry,
				asyncon.address [0], 
				asyncon.address [1], 
				asyncon.connected,
				request.uri,
				route
			), 'warn')
		
		fetcher = http_request.HTTPRequest (psysicaluri, request.command, collector is not None, logger = self.wasc.logger.get ("server"))		
		r = proxy_handler.ProxyRequestHandler (asyncon, fetcher, self.callback, request, collector)
		r.start ()
	
	def callback (self, handler):
		request, response, collector = handler.client_request, handler.response, handler.collector
		cluster = self.find_cluster (request)
		
		cluster.report (handler.asyncon, response.code)	
		
		if response.code < 100:
			if request.loadbalance_retry >= len (cluster):
				request.response.error (506, "%s (Code: 506.%d)" % (response.msg, response.code))
				
			elif request.channel:
				if not collector or (collector and collector.cached):
					if collector:
						collector.reuse_cache ()
					self.route (request, collector)
					return self.dealloc (request, handler)
					
		else:
			try:	
				self.save_cache (request, handler)					
			except:
				self.wasc.logger.trace ("server")
		
		request.loadbalance_retry = 0		
		self.dealloc (request, handler)		
		