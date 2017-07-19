from skitai.server.http_request import http_request
from aquests.protocols.http import http_util

DEFAULT_HEADERS = {
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
	"Accept-Encoding": "gzip, deflate, br",
	"Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.6,en;q=0.4",
	"Referer": "https://pypi.python.org/pypi/skitai",
	"Upgrade-Insecure-Requests": 1,
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
}
REQUEST = "GET %s HTTP/1.0"

def make_header (url = "/", headers = []):
	request = REQUEST % url
	copied = DEFAULT_HEADERS.copy ()
	for k, v in headers:
		copied [k] = v
	headers = "\r\n".join (["%s: %s" % h for h in copied.items ()])
	return request, headers

def test_request (channel):	
	requri, headers = make_header ("/")
	command, uri, version = http_util.crack_request (requri)	
	request = http_request (channel,  requri, command, uri, version, headers)
	