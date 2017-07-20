from confutil import client, rprint, assert_request
import confutil
import skitai
import os

def test_default_handler (wasc):
	vh = confutil.install_vhost_handler (wasc)
	vh.add_route ("default", "/ = ./examples/statics", None)
		
	request = client.get ("http://www.skitai.com/1001.htm")
	assert_request (vh, request, 404)
	
	request = client.get ("http://www.skitai.com/100.htm")	
	resp = assert_request (vh, request, 200)
	assert resp.get_header ('cache-control') is None
	
	request = client.get ("http://www.skitai.com/img/reindeer.jpg")
	resp = assert_request (vh, request, 200)
	assert resp.get_header ('cache-control')
	
def test_wsgi_handler (wasc, app):
	@app.route ("/")
	def index (was):
		return "Hello"
	
	@app.route ("/json")
	def json (was):
		return "Hello"
	
	# WSGI
	vh = confutil.install_vhost_handler (wasc)
	root = confutil.getroot ()
	pref = skitai.pref ()
	vh.add_route ("default", ("/", app, root), pref)
	
	request = client.get ("http://www.skitai.com/")	
	resp = assert_request (vh, request, 200)	
	assert resp.text == "Hello"
	
	request = client.get ("http://www.skitai.com/a")	
	resp = assert_request (vh, request, 404)
	
	request = client.get ("http://www.skitai.com/?a=b")	
	resp = assert_request (vh, request, 508)
	
	request = client.post ("http://www.skitai.com/json", {'a': 1})	
	resp = assert_request (vh, request, 200)
	
	confutil.enable_threads ()
	assert wasc.numthreads == 1
	assert wasc.threads
	
	request = client.post ("http://www.skitai.com/json", {'a': 1})	
	resp = assert_request (vh, request, 200)
	
	confutil.disable_threads ()
	assert wasc.numthreads == 0
	assert wasc.threads is None
	
	request = client.post ("http://www.skitai.com/json", {'a': 1})	
	resp = assert_request (vh, request, 200)
	
	