from rs4.protocols.http import request
from rs4.protocols.grpc import request as grpc_request
from rs4.protocols.ws import request as ws_request
from rs4.protocols.dbi import request as dbo_request
from examples.services import route_guide_pb2

def test_request_attrs ():
	point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
	payload = {'file': open ('./examples/statics/100.htm', "rb")}
	url = "http://127.0.0.1/"
	rs = [
		request.XMLRPCRequest,
		request.JSONRPCRequest,
		request.HTTPRequest,
		request.HTTPMultipartRequest,
		request.XMLRPCRequest,
		grpc_request.GRPCRequest,
		ws_request.Request,
		dbo_request.Request
	]

	for attr in ('reauth_count', 'retry_count'):
		for r in rs:
			assert hasattr (r, attr)

