from rs4 import logger
from skitai.rpc import cluster_manager, task
from skitai.threads import trigger
import sys
from rs4 import asyncore
import time
from aquests.client import socketpool
import threading

def __reduce (asyncall):
	for rs in asyncall.getswait (timeout = 5):
		print("Result:", rs.status, rs.code, repr(rs.get_content ()))
				
def testCluster ():	
	sc = cluster_manager.ClusterManager ("tt", ["hq.lufex.com:5000 1",], logger= logger.screen_logger ())
	clustercall = task.TaskCreator (sc, logger.screen_logger ())	
	s = clustercall.Server ("/websocket/echo", "Hello WS Cluster", "ws", auth = ("app", "1111"), mapreduce = False)
	threading.Thread (target = __reduce, args = (s,)).start ()
	while 1:		
		asyncore.loop (timeout = 1, count = 2)
		if len (asyncore.socket_map) == 1:
			break

def testSocketPool ():
	sc = socketpool.SocketPool (logger.screen_logger ())
	clustercall = task.TaskCreator (sc, logger.screen_logger ())			
	s = clustercall.Server ("http://hq.lufex.com:5000/websocket/echo", "Hello WS Sock Pool", "ws", auth = ("app", "1111"))
	#s = clustercall.Server ("http://210.116.122.187:3424/rpc2", "admin/whddlgkr")
	#s.bladese.util.status ("openfos.v2")
	
	threading.Thread (target = __reduce, args = (s,)).start ()
	
	while 1:
		asyncore.loop (timeout = 1, count = 2)
		print(asyncore.socket_map)
		if len (asyncore.socket_map) == 1:
			break

trigger.start_trigger ()
testSocketPool ()
testCluster ()


