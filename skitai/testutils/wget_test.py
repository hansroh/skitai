from skitai.protocol.http import wget
from skitai.lib import logger

wget.configure (logger.screen_logger (), 3, 2)

def handle_response (response):
	print (response.request.get_eurl () ["rfc"])
			
wget.add ("GET http://www.openfos.com --http-proxy hq.lufex.com:5000", handle_response)
wget.add ("GET https://pypi.python.org/pypi --http-proxy hq.lufex.com:5000", handle_response)
wget.add ("GET http://hellkorea.com/xe/", handle_response)
wget.add ("GET http://www.hungryboarder.com/index.php?mid=Rnews&category=470", handle_response)
wget.add ("GET http://mailtemplate.lufex.com/search.cfm?k=rachmani+weissen", handle_response)
wget.add ("GET http://paxnet.moneta.co.kr/stock/intro/analysis.jsp", handle_response)

wget.get_all ()

