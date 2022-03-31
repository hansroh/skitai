from confutil import rprint
import confutil
import skitai
import os, pytest
from skitai.testutil import offline as testutil
from skitai.testutil.offline import client as cli

CLIENT = None

def assert_request (handler, request, expect_code):
	global CLIENT

	resp = CLIENT.handle_request (request, handler)
	assert resp.status_code == expect_code, rprint ("STATUS CODE:", resp.status_code)
	return resp


@pytest.mark.run (order = 1)
def test_default_handler (client):
	global CLIENT
	CLIENT = client

	vh = testutil.install_vhost_handler ()
	testutil.mount ("/", "./examples/statics")

	request = client.get ("http://www.skitai.com/1001.htm")
	assert_request (vh, request, 404)

	request = client.get ("http://www.skitai.com/100.htm")
	resp = assert_request (vh, request, 200)
	assert resp.get_header ('cache-control') is None

	request = client.get ("http://www.skitai.com/img/reindeer.jpg")
	resp = assert_request (vh, request, 200)
	assert resp.get_header ('cache-control')

	request = client.get ("http://www.skitai.com/img/reindeer.jpg", version = "2.0")
	resp = assert_request (vh, request, 200)
	assert resp.get_header ('cache-control')

