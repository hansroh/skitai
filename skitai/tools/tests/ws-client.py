from __future__ import print_function
from skitai import requests
from skitai.lib import logger

def handle_page (rc):		
	#print (rc.response.get_header ("opcode"))
	rc.logger ("[info] response code: %d, %s %s" % (rc.response.code, rc.uinfo.rfc, rc.response.binary ()))
	
	

if __name__ == "__main__":				
	requests.configure (logger.screen_logger (), 1, 20)
	#requests.add ("ws://app:1111@hq.lufex.com:5000/websocket/echo --wsoc-message hello 1, hans", handle_page)
	#requests.add ("ws://app:1111@hq.lufex.com:5000/websocket/echo --wsoc-message hello 2, hans", handle_page)
	#requests.add ("http://app:1111@hq.lufex.com:5000/ --http-connection keep-alive", handle_page)
	#requests.add ("http://app:1111@ibizcast.skitai.com:5000/ --http-connection keep-alive", handle_page)
	#requests.add ("https://gitlab.com/u/hansroh --http-tunnel hq.lufex.com:5000", handle_page)
	requests.add ("ws://52.53.252.193:5000/websocket/echo --wsoc-message hello 1, hans --http-tunnel hq.lufex.com:5000", handle_page)
	#requests.add ("ws://52.53.252.193:5000/websocket/echo --wsoc-message hello 1, hans", handle_page)
	#requests.add ("ws://52.53.252.193:5000/websocket/echo --wsoc-message hello 2, hans", handle_page)
	requests.get_all ()
	
	
