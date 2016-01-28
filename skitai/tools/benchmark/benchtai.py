from __future__ import print_function
from skitai import requests
from skitai.lib import logger
import time


class timer:
	def __init__ (self):
		self.start = time.time()
	def end (self):
		return time.time() - self.start
				

def handle_response (rc):
	global total_sessions, clients, req, total_errors, resp_codes
	
	#print (rc.response.header)	
	total_sessions += 1
	try: resp_codes [rc.response.code] += 1
	except KeyError: resp_codes [rc.response.code] = 1
	if rc.response.code != 200: total_errors += 1
		
	print (total_sessions, end = " ")
	#print ("\r\n".join (rc.response.header))
	if total_sessions <= clients * req - clients:
		requests.add (url, handle_response)


def usage ():
	print ("%s [options] url" % sys.argv [0])
	print (" -c		concurrent clients (default: 1)")
	print (" -r		reuqests per clients (default: 1)")
	print (" -k		use keep-alive (default: no)")
	print (" --help		show help")
	

if __name__ == '__main__':
	import getopt, sys
	argopt, args = getopt.getopt (sys.argv[1:], "c:r:k", ["help"])
		
	clients = 1
	req = 1
	
	total_sessions = 0
	total_errors = 0
	resp_codes = {}
	use_keep_alive = False
	
	try:
		url = args [0]
	except IndexError:
		usage ()
		sys.exit ()	
	
	for k, v in argopt:
		if k == "-c": 
			clients = int (v)
		elif k == "-r":	
			req = int (v)
		elif k == "-k":	
			use_keep_alive = True
		elif k == "--help":		
			usage ()
			sys.exit ()
	
	requests.configure (
		logger.screen_logger (), 
		clients, 
		10, 
		default_option = "--http-connection " + (use_keep_alive and "keep-alive" or "close")
	)
	
	for i in range (clients):
		requests.add (url, handle_response)
	
	t = timer()
	requests.get_all ()
	total_time = t.end()
	
	print((
		'\n%d clients\n%d hits/client\n'
		'total hits:%d\n'
		'total errors:%d\n%.3f seconds\ntotal hits/sec:%.3f' % (
			clients,
			req,
			total_sessions,
			total_errors,
			total_time,
			total_sessions / total_time
		)
	))
						
	codes = list(resp_codes.items ())
	codes.sort (key = lambda x: x [1], reverse = True)
	print ("----------------------------\nresponse codes status")
	for each in codes:
		print ("%d: 	%d" % each)
