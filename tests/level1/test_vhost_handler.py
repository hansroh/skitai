from confutil import rprint, assert_request
import confutil
import skitai
import os, pytest
from skitai import testutil

@pytest.mark.run (order = 1)
def test_default_handler (wasc, client):
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
	
@pytest.mark.run (order = 2)	
def test_wsgi_handler (wasc, app, client):
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
