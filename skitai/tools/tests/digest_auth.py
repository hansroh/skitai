from __future__ import print_function
from skitai.protocol.http import requests
from skitai.lib import logger
import time


def handle_response (rc):
	global total_sessions, clients, req, total_errors, resp_codes
	print (rc.response.code)
	
requests.configure (
	logger.screen_logger (), 
	2, 
	10, 
	default_option = "--http-connection close"
)

requests.add ("http://app:1111@hq.lufex.com:5000/hello", handle_response)
requests.get_all ()
