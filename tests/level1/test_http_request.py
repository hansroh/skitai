from skitai.protocols.sock.impl.http import http_util
from confutil import rprint
from examples.services import route_guide_pb2

def test_request_generation (client):
	url = "http://www.skitai.com/index"

	# GET
	request = client.get (url)
	assert request.command == "get"
	assert request.method == "GET"
	assert request.uri == "/index"
	assert request.version == "1.1"

	# POSTS
	# empty body
	request = client.post (
		url, '',
		headers = [("Content-Type", "application/x-www-form-urlencoded")]
	)
	assert request.body is None

	payload = {"a": 1, "b": "z"}
	request = client.post (
		url, payload,
		headers = [("Content-Type", "application/x-www-form-urlencoded")]
	)
	rprint (request.get_header ('content-type'))
	assert request.command == "post"
	assert request.body in (b'a=1&b=z', b'b=z&a=1')
	assert request.get_header ('content-type') == "application/x-www-form-urlencoded; charset=utf-8"

	request = client.post (
		url, payload,
		headers = [("Content-Type", "application/json")]
	)
	assert request.get_header ('content-length') == "18"
	assert request.body in (b'{"b": "z", "a": 1}', b'{"a": 1, "b": "z"}')
	assert request.get_header ('content-type') == "application/json; charset=utf-8"

	request = client.postjson (url, payload)
	assert request.body in (b'{"b": "z", "a": 1}', b'{"a": 1, "b": "z"}')
	assert request.get_header ('content-type') == "application/json; charset=utf-8"

	# UPLOAD
	payload.pop ("a")
	payload ['file'] = open ('./examples/statics/100.htm', "rb")
	request = client.upload (url, payload)
	assert request.get_header ('content-type').startswith ("multipart/form-data;")
	assert request.body.startswith (b"-----") and len (request.body) == 433
	assert request.get_header ('content-length') == "433"

	# XMLRPC
	request = client.xmlrpc_request (url).calucator.add ("A", 1)
	rprint (request.get_header ('content-length'))
	assert request.body.startswith (b"<?xml") and len (request.body) == 203
	assert request.get_header ('content-type') == "text/xml; charset=utf-8"
	assert request.get_header ('content-length') == "203"

	# JSONRPC
	request = client.jsonrpc_request (url).calucator.add ("A", 1)
	assert request.body.startswith (b"{\"") and len (request.body) in (103, 111)
	assert request.get_header ('content-type') == "application/json-rpc; charset=utf-8"
	assert request.get_header ('content-length') in ("103", "111")

	# GRPC
	url = "http://www.skitai.com/routeguide.RouteGuide"
	point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
	request = client.grpc_request (url).GetFeature (point)
	rprint (request.get_header ('content-length'))
	assert request.get_header ('content-type') == "application/grpc+proto"
	assert request.body.startswith (b'\x00\x00\x00\x00\x11') and len (request.body) == 22
	assert request.get_header ('content-length') is None
	assert request.version == "2.0"


def test_request (client):
	url = "http://www.skitai.com/index"
	request = client.get (url)
	assert request.get_header ("content-type") is None
	assert request.get_header ("content-type", 'pytest') == 'pytest'
	assert request.get_header ("Accept-Language") == "en-US,en;q=0.8,en-US;q=0.6,en;q=0.4"
	v, p = request.get_header_params ("Accept-Language")
	assert v == "en-US,en"
	assert p ['q'] == '0.4'
	assert request.get_header_noparam ("Accept-Language") == "en-US,en"
	assert request.get_attr ("Accept-Language") == {"q": "0.4"}
	assert request.get_attr ("Accept-Language", "q") == "0.4"
	assert request.get_attr ("Accept-Language", "x") is None
	assert request.get_attr ("Accept-Language", "x", "") == ""
	assert request.get_content_length () is None

def test_header_funcs (client):
	url = "http://www.skitai.com/index"
	request = client.post (url, {"a": "b"}, headers = [("Content-Type", "application/json; charset=utf8")])
	assert request.get_content_type () == "application/json"
	assert request.get_main_type () == "application"
	assert request.get_sub_type () == "json"
	assert request.get_charset () == "utf-8"
	assert request.get_content_length () == 10
	assert request.get_user_agent () == "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
	assert request.get_body () == request.body == b'{"a": "b"}'

def test_uri_funcs (client):
	url = "http://www.skitai.com/index"
	request = client.get (url)
	assert request.split_uri () == ('/index', None, None, None)

	url = "http://www.skitai.com/index;SESSIONID=das4534gdfd"
	request = client.get (url)
	rprint (request.split_uri ())
	assert request.split_uri () == ('/index', ';SESSIONID=das4534gdfd', None, None)

	url = "http://www.skitai.com/index;SESSIONID=das4534gdfd?a=b#id-454"
	request = client.get (url)
	assert request.split_uri () == ('/index', ';SESSIONID=das4534gdfd', '?a=b', None)

	rprint (request.get_gtxid (), request.get_ltxid ())

	assert len (request.get_gtxid ()) == 10
	assert request.get_ltxid ()[:3] == '100'
