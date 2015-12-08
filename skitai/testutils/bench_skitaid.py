from __future__ import print_function
from skitai.protocol.http import requests
from skitai.lib import logger
import random


CLI = 10
REQ = 100
TREQ = 0

requests.configure (logger.screen_logger (), CLI, 10)

L = [
			"/test/db",
			"/test/dlb",
			"/test/dmap",
			"/test/lb",
			"/test/lb2",
			"/test/lb3",
			"/test/map",
			"/test/map2",
			"/test/map3",
			"/images/concept.png",
			"/test/rpc",
			"/test/wget",
			"/reverseproxy",
			"/test/options",
			"/test/upload"
]

L = ["/"]

def handle_response (rc):
	global TREQ, CLI, REQ	
	TREQ += 1
	print (rc.response.code, end = " ")
	#print ("\r\n".join (rc.response.header))
	if TREQ <= CLI * REQ:
		requests.add ("http://54.67.113.190:5000%s" % random.choice (L), handle_response)

for i in range (CLI):
	requests.add ("http://54.67.113.190:5000%s" % random.choice (L), handle_response)

requests.get_all ()

