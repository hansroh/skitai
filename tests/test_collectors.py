import confutil
from confutil import rprint, client
from skitai.server.handlers import collectors
from skitai.saddle import grpc_collector
from examples.package import route_guide_pb2
from skitai.saddle import multipart_collector
from mock import MagicMock
import pytest

@pytest.fixture
def handler (wasc):
	return confutil.install_vhost_handler (wasc)

@pytest.fixture
def post ():
	return client.post ("http://www.skitai.com/", {"a": "b"})	

@pytest.fixture
def multipart ():
	return client.upload ("http://www.skitai.com/", {"a": "b", "file": open ('./examples/statics/reindeer.jpg', "rb")})	

@pytest.fixture
def grpc ():
	point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
	return client.grpc ("http://www.skitai.com/routeguide.RouteGuide", "GetFeature", (point,))
				
def test_form_collector (handler, post):
	c = collectors.FormCollector (handler, post)

def test_h2dummy_collector (handler, post):	
	c = collectors.HTTP2DummyCollector (handler, post, 200)
		
def test_multipart_collector (handler, multipart):
	c = collectors.MultipartCollector (handler, multipart, 1024, 2048, 512)
	
def test_saddle_multipart_collector (handler, multipart):
	c = multipart_collector.MultipartCollector (handler, multipart, 1024, 2048, 512)

def test_saddle_grpc_collector (handler, grpc):
	c = grpc_collector.grpc_collector (handler, grpc)
	
