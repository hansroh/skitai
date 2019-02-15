from aquests.protocols.http import request
from aquests.protocols.grpc import request as grpc_request
from aquests.protocols.ws import request as ws_request
from aquests.dbapi import request as dbo_request
from examples.package import route_guide_pb2

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
		
