from . import wsgi_handler, proxy_handler
from skitai.protocol.http import request as http_request
import re
	
class Handler (proxy_handler.Handler):
	def __init__ (self, wasc, clusters, cachefs = None):
		proxy_handler.Handler.__init__ (self, wasc, clusters, cachefs)
		self.route_map = {}
	
	def add_route (self, route, cname):		
		self.route_map [route] = (cname, len (route), re.compile (route + "(?P<rti>[0-9]*)", re.I))
	
	def match (self, request):		
		return self.find_cluster (request) and 1 or 0
				
	def find_cluster (self, request):
		uri = request.uri
		for route, (cname, route_len, route_rx) in list (self.route_map.items ()):		
			match = route_rx.match (uri)
			if match:
				return self.clusters [cname], route_len, route_rx
	
	def is_tunneling (self):		
		return self.response.code == 101 # upgrade
			
	def handle_request (self, request):
		proxy_handler.Handler.handle_queued_request (self, request)
							
	def continue_request (self, request, collector):
		request.loadbalance_retry = 0
		if self.is_cached (request, collector is not None):
			return
		
		try:
			self.route (request, collector)			
		except:
			self.wasc.logger.trace ("server")	
			request.response.error (500, "", "Routing failed. Please contact administator.")
	
	def route (self, request, collector):
		current_cluster, route_len, route_rx  = self.find_cluster (request)		
		maybe_route = route_rx.match (request.uri).group ("rti")
		if maybe_route: 
			route = int (maybe_route)			
		else:
			route = -1
				
		psysicaluri = request.uri [len (maybe_route) + route_len:]
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
		cluster = self.find_cluster (request) [0]
		cluster.report (handler.asyncon, response.code)	
		
		if response.code >= 700:
			if request.loadbalance_retry >= len (cluster):
				request.response.error (506, response.msg)
				
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
		