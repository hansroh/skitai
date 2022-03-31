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

@pytest.mark.run (order = 2)
def test_wsgi_handler (app, client, wasc):
	global CLIENT
	CLIENT = client

	@app.route ("/")
	def index (was, a = 0):
		return "Hello"

	@app.route ("/json")
	def json (was, a):
		return "Hello"

	@app.route ("/rpc2/add")
	def add (was, a, b):
		return a + b

	# WSGI
	vh = testutil.install_vhost_handler ()
	testutil.mount ("/", (app, confutil.getroot ()), skitai.pref ())

	request = client.get ("http://www.skitai.com/")
	resp = assert_request (vh, request, 200)
	assert resp.text == "Hello"

	request = client.get ("http://www.skitai.com/", version = "2.0")
	resp = assert_request (vh, request, 200)
	assert resp.text == "Hello"

	request = client.get ("http://www.skitai.com/a")
	resp = assert_request (vh, request, 404)

	request = client.get ("http://www.skitai.com/?a=b")
	resp = assert_request (vh, request, 200)

	request = client.api ().json.post ({'a': 1})
	resp = assert_request (vh, request, 200)

	answer = client.rpc ("http://www.skitai.com/rpc2/").add (100, 50)
	resp = assert_request (vh, request, 200)

	answer = client.jsonrpc ("http://www.skitai.com/rpc2/").add (100, 50)
	resp = assert_request (vh, request, 200)

	testutil.enable_threads ()
	assert wasc.numthreads == 1
	assert wasc.threads

	request = client.postjson ("http://www.skitai.com/json", {'a': 1})
	resp = assert_request (vh, request, 200)

	request = client.postjson ("http://www.skitai.com/json", {'a': 1}, version = "2.0")
	resp = assert_request (vh, request, 200)

	testutil.disable_threads ()
	assert wasc.numthreads == 0
	assert wasc.threads is None

	request = client.postjson ("http://www.skitai.com/json", {'a': 1})
	resp = assert_request (vh, request, 200)

	request = client.postjson ("http://www.skitai.com/json", {'a': 1}, version = "2.0")
	resp = assert_request (vh, request, 200)
