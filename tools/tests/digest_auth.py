from __future__ import print_function
from skitai.protocols.sock.impl.http import requests
from rs4 import logger
import time


def handle_response (rc):
	global total_sessions, clients, req, total_errors, resp_codes
	print (rc.response.code)

requests.configure (
	logger.screen_logger (),
	2,
	10,
	default_option = "--http-connection keep-alive"
)

requests.add ("http://app:1111@hq.lufex.com:5000/hello", handle_response)
requests.get_all ()
