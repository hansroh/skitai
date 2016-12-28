from . import wsgi_handler, proxy_handler
from skitai.protocol.http import request as http_request
import re


class Handler (proxy_handler.Handler):
	def __init__ (self, wasc, clusters, cachefs = None):
		proxy_handler.Handler.__init__ (self, wasc, clusters, cachefs)
		self.route_map = {}
		self.sorted_route_map = []
	
	def add_route (self, route, cname):		
		self.route_map [route] = (cname, len (route), re.compile (route + "(?P<rti>[0-9]*)", re.I))
		temp = list (self.route_map.items ())
		temp.sort (key = lambda x: x [1][1], reverse = True)
		self.sorted_route_map = temp
		
	def match (self, request):		
		return self.find_cluster (request) and 1 or 0
				
	def find_cluster (self, request):
		uri = request.uri
		for route, (cname, route_len, route_rx) in self.sorted_route_map:
			match = route_rx.match (uri)
			if match:				
				return self.clusters [cname], route_len, route_rx		
		
	def will_open_tunneling (self):
		return self.response.code == 101 # websocket connection upgrade

	def continue_request (self, request, collector):
		request.loadbalance_retry = 0
		if self.has_valid_cache (request, collector is not None):
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
		retry = request.loadbalance_retry
		asyncon = current_cluster.get (index = route)
		
		if not asyncon: 
			request.logger ("nopool-%d, url: %s, cluster index: %d" % (
				retry, 
				request.uri, 
				route
				), 'warn')
			return request.response.error (503)
		
		if retry > 1:
			request.logger ("failsafe-%d, target: %s:%s, url: %s, cluster index: %d" % (
				retry,
				asyncon.address [0], 
				asyncon.address [1],				
				request.uri,
				route
			), 'warn')
		
		fetcher = http_request.HTTPRequest (psysicaluri, request.command, collector is not None, logger = self.wasc.logger.get ("server"))		
		r = proxy_handler.proxy_request_handler (asyncon, fetcher, self.callback, request, collector)	
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
		