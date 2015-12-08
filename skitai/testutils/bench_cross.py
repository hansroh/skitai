from __future__ import print_function
from skitai.protocol.http import requests
from skitai.lib import logger
import time

clients = 100
req = 3
total_sessions = 0
total_errors = 0
resp_codes = {}
port = 5000

requests.configure (logger.screen_logger (), clients, 60, default_option = "--http-connection keep-alive")
L = ["/"]

class timer:
	def __init__ (self):
		self.start = time.time()
	def end (self):
		return time.time() - self.start
				

def handle_response (rc):
	global total_sessions, clients, req, total_errors, resp_codes
	
	print (rc.response.header)
	
	total_sessions += 1
	try: resp_codes [rc.response.code] += 1
	except KeyError: resp_codes [rc.response.code] = 1
	if rc.response.code != 200: total_errors += 1
		
	print (total_sessions, end = " ")
	#print ("\r\n".join (rc.response.header))
	if total_sessions <= clients * req - clients:
		requests.add ("http://54.67.113.190:%d/" % port, handle_response)

for i in range (clients):
	requests.add ("http://54.67.113.190:%d/" % port, handle_response)

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
codes.sort ()