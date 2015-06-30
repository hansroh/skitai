import cluster_dist_call
import urlparse
import asynrequest_handler
import time
import threading
from skitai.server.threads import trigger
import asynconnect
import cluster_manager

		
if __name__ == "__main__":
	from skitai.lib  import logger
	import cluster_manager
	import sys
	import asyncore
	
	def in_thread (asyncall):
		rs = asyncall.getwait (10)
		print rs.status, rs.code, `rs.result[:200]`, len (rs.result)

	sc = cluster_manager.SocketFarm (logger.screen_logger ())
	trigger.start_trigger (('127.9.9.9', 19999))
	
	asynrpc = cluster_dist_call.ClusterDistCallCreator (sc, logger.screen_logger ())
	#s = asynrpc.Server ("http://hq.lufex.com:3427/json")
	#s.test ()
	
	s1 = asynrpc.Server ("https://secure.lufex.com")	
	s1.request ("/ggpark/a.log")
	
	threading.Thread (target = in_thread, args = (s1,)).start ()		
	
	
	while 1:
		asyncore.loop (timeout = 1, count = 2)
		if len (asyncore.socket_map) == 1:
			break






