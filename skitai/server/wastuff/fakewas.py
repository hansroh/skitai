from .. import wsgiappservice
from .. import wsgi_apps, http_request
from ..http_server import http_server, http_channel
from .triple_logger import Logger
from aquests.protocols.http import http_util

logger = Logger (["screen"], None)

class Channel (http_channel):
	pass
	
		
DEFAULT_HEADERS = {
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
	"Accept-Encoding": "gzip, deflate, br",
	"Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.6,en;q=0.4",
	"Referer": "https://pypi.python.org/pypi/skitai",
	"Upgrade-Insecure-Requests": 1,
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
}
REQUEST = "GET / HTTP/1.0"

def build (app):
	wasc = wsgiappservice.WAS
	was = wasc ()
	was.app = app
	was.app._was = was
	
	command, uri, version = http_util.crack_request (REQUEST)	
	channel = Channel (
		http_server ('0.0.0.0', 65000, logger.get ('server'), logger.get ('request')), 
		None, ('127.0.0.1', 0)
	)
	
	was.request = http_request.http_request (
		channel, REQUEST,
		command, uri, version,
		DEFAULT_HEADERS
	)
	was.response = was.request.response
	return was

