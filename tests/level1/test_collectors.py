import confutil
from skitai.handlers import collectors
from atila.collectors import grpc_collector
try:
	from examples.services import route_guide_pb2
except ImportError:
	from examples.services import route_guide_pb2_v3 as route_guide_pb2
from atila.collectors import multipart_collector
import pytest
from skitai.testutil import offline as testutil

@pytest.fixture
def handler (Context):
	return testutil.install_vhost_handler ()

@pytest.fixture
def post (client):
	return client.post ("http://www.skitai.com/", {"a": "b"})

@pytest.fixture
def multipart (client):
	return client.upload ("http://www.skitai.com/", {"a": "b", "file": open ('./examples/statics/reindeer.jpg', "rb")})

@pytest.fixture
def grpc (client):
	point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
	return client.grpc_request ("http://www.skitai.com/routeguide.RouteGuide").GetFeature (point)

def test_form_collector (handler, post):
	c = collectors.FormCollector (handler, post)

def test_h2dummy_collector (handler, post):
	c = collectors.HTTP2DummyCollector (handler, post, 200)

def test_multipart_collector (handler, multipart):
	c = multipart_collector.MultipartCollector (handler, multipart, 1024, 2048, 512)

def test_alita_multipart_collector (handler, multipart):
	c = multipart_collector.MultipartCollector (handler, multipart, 1024, 2048, 512)

def test_alita_grpc_collector (handler, grpc):
	c = grpc_collector.GRPCCollector (handler, grpc)
