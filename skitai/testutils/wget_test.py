from skitai.protocol.http import wget
from skitai.lib import logger


wget.init (logger.screen_logger ())


def handle_response (response):
	print (repr (response.get_content()[:120]))

wget.add ("GET http://www.openfos.com --http-proxy hq.lufex.com:5000", handle_response)
wget.add ("GET https://pypi.python.org/pypi --http-proxy hq.lufex.com:5000", handle_response)
wget.get_all ()

wget.close ()


