from skitai.protocol.http import requests
from skitai.lib import logger

requests.configure (logger.screen_logger (), 3, 2)

def handle_response (rc):
	print (repr (rc.uinfo.rfc), repr (rc.response.encoding))
	print ("-" * 79)
	#print ("\r\n".join (rc.response.header))
	#print ("-" * 79)
	#print (rc.request.uri, rc.request.version)
	#print ("\r\n".join (rc.request.header))
	print ("=" * 79)

requests.add ("GET http://hq.lufex.com:5000/test/map", handle_response)
#requests.add ("GET https://pypi.python.org/pypi --http-proxy hq.lufex.com:5000", handle_response)
#requests.add ("GET http://hellkorea.com/xe/", handle_response)
#requests.add ("GET http://www.hungryboarder.com/index.php?mid=Rnews&category=470", handle_response)
#requests.add ("GET http://mailtemplate.lufex.com/search.cfm?k=rachmani+weissen", handle_response)
#requests.add ("GET http://paxnet.moneta.co.kr/stock/intro/analysis.jsp", handle_response)

requests.get_all ()

