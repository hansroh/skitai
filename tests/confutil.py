from aquests.protocols.http import http_util
from skitai.server.http_request import http_request

DEFAULT_HEADERS = {
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
	"Accept-Encoding": "gzip, deflate, br",
	"Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.6,en;q=0.4",
	"Referer": "https://pypi.python.org/pypi/skitai",
	"Upgrade-Insecure-Requests": 1,
	"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
}
REQUEST = "%s %s HTTP/%s"
CHANNEL = None

class Client:
	def make_request (self, method = "GET", uri = "/", data = None, headers = [], version = "1.1"):
		requri = REQUEST % (method.upper (), uri, version)
		copied = DEFAULT_HEADERS.copy ()
		for k, v in headers:
			copied [k] = v
		headers = "\r\n".join (["%s: %s" % h for h in copied.items ()])
		command, uri, version = http_util.crack_request (requri)	
		request = http_request (CHANNEL,  requri, command, uri, version, headers)	
		if data:
			request.set_body (data)
		return request
	
	def get (self, uri, headers = [], version = "1.1"):
		return self.make_request ("GET", uri, None, headers, version)
	
	def delete (self, uri, headers = [], version = "1.1"):
		return self.make_request ("DELETE", uri, None, headers, version)
		
	def post (self, uri, data, headers = [], version = "1.1"):
		return self.make_request ("POST", uri, data, headers, version)	
	
	def patch (self, uri, data, headers = [], version = "1.1"):
		return self.make_request ("PATCH", uri, data, headers, version)	
	
	def put (self, uri, data, headers = [], version = "1.1"):
		return self.make_request ("PUT", uri, data, headers, version)	
	
client = Client ()
