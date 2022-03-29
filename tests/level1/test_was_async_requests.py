import confutil
import pytest

def check_success (resp):
    pass

def test_was_async_requests (async_wasc, app, client, dbpath):
    was = async_wasc ()
    was.app = app

    #----------------------------------------
    was.request = client.get ("/")
    cdc = was.get ("@example/", callback = check_success)
    request = cdc._request
    assert request.get_header ("accept") == "application/json"
    assert request.get_header ("x-ltxn-id") == "1001"
    assert request.get_header ("content-type") is None
    assert request.get_payload () == b''
    assert request.method == "get"
    assert request.uri == "/"
    assert request.params is None
    assert request.auth is None
    assert not request.xmlrpc_serialized ()

    #----------------------------------------
    app.config.default_request_type = ("x-form/url-encoded", "text/html")
    cdc = was.get ("@example/xxx?", callback = check_success)
    request = cdc._request
    assert request.uri == "/xxx?"
    assert request.get_header ("accept") == "text/html"

    #----------------------------------------
    app.config.default_request_type = None
    cdc = was.post ("@example/xxx?", callback = check_success)
    request = cdc._request
    assert request.method == "post"
    assert request.get_header ("accept") == "application/json"
    assert request.get_header ("content-type") is None
    assert request.get_header ("content-length") == 0
    assert request.get_payload () == b''

    #----------------------------------------
    cdc = was.post ("@example/xxx?", {"a": 1}, callback = check_success)
    request = cdc._request
    assert request.method == "post"
    assert request.get_header ("accept") == "application/json"
    assert request.get_header ("content-type") == "application/json; charset=utf-8"
    assert request.get_header ("content-length") == 8
    assert request.get_payload () == b'{"a": 1}'

    #----------------------------------------
    cdc = was.upload ("@example/xxx?", {"a": "Hi", "b": open (__file__, "r")}, callback = check_success)
    request = cdc._request
    assert request.method == "upload"
    assert request.get_method () == "POST"
    assert request.get_header ("accept") == "application/json"
    assert request.get_header ("content-type").startswith ("multipart/form-data; boundary=-------------------")
    assert request.get_header ("content-length") > 1000
    pl = request.get_payload ()
    for i in range (3):
        pl.more ()
    data = b"".join (pl.serialized)
    assert b'form-data; name="a"' in data
    assert b'filename="test_was_async_requests.py"' in data
    assert b"import confutil" in data

    #----------------------------------------
    cdc = was.ws ("@example/xxx?", "Hello Websocket", callback = check_success)
    request = cdc._request
    assert request.uri == "/xxx?"
    assert request.method == "websocket"
    assert request.message == "Hello Websocket"
    assert request.params == {}
    assert request.get_method () == "WEBSOCKET"
    assert request.get_header ("accept") == "*/*"
    assert request.get_header ("content-type")is None
    assert request.get_header ("content-length") is None
    pl = request.get_payload ()
    packet = pl.more ()
    assert isinstance (packet, bytearray)
    assert len (packet) == 21

    #----------------------------------------
    stub = was.xmlrpc ("@example/xxx?", callback = check_success)
    cdc = stub.math.addnumber (1, 2)
    request = cdc._request
    assert request.uri == "/xxx?/"
    assert request.method == "math.addnumber"
    assert request.params == (1, 2)
    assert request.get_method () == "POST"
    assert request.get_header ("accept") == "*/*"
    assert request.get_header ("content-type").startswith ("text/xml; charset=utf-8")
    assert request.get_header ("content-length") > 180
    pl = request.get_payload ()
    assert b"<methodName>math.addnumber</methodName>" in pl

    #----------------------------------------
    stub = was.jsonrpc ("@example/xxx?", callback = check_success)
    cdc = stub.math.addnumber (1, 2)
    request = cdc._request
    assert request.method == "math.addnumber"
    assert request.params == (1, 2)
    assert request.get_method () == "POST"
    assert request.get_header ("accept") == "*/*"
    assert request.get_header ("content-type").startswith ("application/json-rpc; charset=utf-8")
    assert request.get_header ("content-length") > 100
    pl = request.get_payload ()
    assert b"math.addnumber" in pl

    #----------------------------------------
    stub = was.grpc ("@example/routeguide.RouteGuide", callback = check_success)
    point = confutil.route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
    cdc = stub.GetFeature (point)
    request = cdc._request
    assert request.uri == "/routeguide.RouteGuide/GetFeature"
    assert request.method == "GetFeature"
    assert request.params == (point,)
    assert request.get_method () == "POST"
    assert request.get_header ("accept") is None
    assert request.get_header ("content-type").startswith ("application/grpc+proto")
    assert request.get_header ("grpc-accept-encoding") == "identity,gzip"
    pl = request.get_payload ()
    assert pl.more () == b'\x00\x00\x00\x00\x11\x08\x9a\xa6\x8c\xc3\x01\x10\x96\x9f\x98\x9c\xfd\xff\xff\xff\xff\x01'

