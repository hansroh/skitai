from confutil import rprint, assert_request
import confutil
import skitai
import os, pytest
from skitai.testutil import offline as testutil

def test_params (wasc, app, client):
	def z (was):
		k = list (was.request.args.keys ())
		k.sort ()
		return " ".join (k)

	@app.route ("/do", methods = ["GET", "POST"])
	def index (was):
		return z (was)

	@app.route ("/do2", methods = ["GET", "POST"])
	def index2 (was, a):
		return z (was)

	@app.route ("/do3/<u>", methods = ["GET", "POST"])
	def index3 (was, **args):
		return z (was)

	@app.route ("/do4/<u>", methods = ["GET", "POST"])
	def index4 (was, u, a, b):
		return z (was)

	@app.route ("/do5/<u>", methods = ["GET", "POST"])
	def index5 (was, u, a):
		return z (was)

	@app.route ("/do6", methods = ["GET", "POST"])
	def index6 (was, a):
		return z (was)

	# WSGI
	vh = testutil.install_vhost_handler ()
	root = confutil.getroot ()
	pref = skitai.pref ()
	vh.add_route ("default", ("/", app, root), pref)

	request = client.get ("http://www.skitai.com/do")
	resp = assert_request (vh, request, 200)
	assert resp.text == ""

	request = client.get ("http://www.skitai.com/do6?a=1")
	resp = assert_request (vh, request, 200)
	assert resp.text == "a"

	request = client.post ("http://www.skitai.com/do6", {'a': 1})
	resp = assert_request (vh, request, 200)
	assert resp.text == "a"

	request = client.postjson ("http://www.skitai.com/do6", {'a': 1})
	resp = assert_request (vh, request, 200)
	assert resp.text == "a"

	request = client.get ("http://www.skitai.com/do?a=1")
	resp = assert_request (vh, request, 200)

	request = client.post ("http://www.skitai.com/do", {'a': 1})
	resp = assert_request (vh, request, 200)

	request = client.postjson ("http://www.skitai.com/do", {'a': 1})
	resp = assert_request (vh, request, 200)

	#----------------------------------------

	request = client.get ("http://www.skitai.com/do2")
	resp = assert_request (vh, request, 400)

	request = client.get ("http://www.skitai.com/do2?a=1")
	resp = assert_request (vh, request, 200)
	assert resp.text == "a"

	request = client.get ("http://www.skitai.com/do2?a=1&b=1")
	resp = assert_request (vh, request, 400)

	request = client.post ("http://www.skitai.com/do2", {'a': 1, 'b': 1})
	resp = assert_request (vh, request, 400)

	request = client.post ("http://www.skitai.com/do2?a=1", {'b': 1})
	resp = assert_request (vh, request, 200)
	assert resp.text == "a b"

	request = client.post ("http://www.skitai.com/do2", {'a': 1})
	resp = assert_request (vh, request, 200)
	assert resp.text == "a"

	#------------------------------------------

	request = client.post ("http://www.skitai.com/do3/1", {'a': 1})
	resp = assert_request (vh, request, 200)

	request = client.post ("http://www.skitai.com/do4/1?a=1", {'b': 1})
	resp = assert_request (vh, request, 200)
	assert resp.text == "a b u"

	request = client.post ("http://www.skitai.com/do4/1?b=1", {'a': 1})
	resp = assert_request (vh, request, 200)
	assert resp.text == "a b u"

	request = client.post ("http://www.skitai.com/do4/1?b=1", {'a': 1})
	resp = assert_request (vh, request, 200)
	assert resp.text == "a b u"

	request = client.post ("http://www.skitai.com/do5/1?b=1", {'a': 1})
	resp = assert_request (vh, request, 400)

	request = client.post ("http://www.skitai.com/do5/1?a=1", {'b': 1})
	resp = assert_request (vh, request, 200)
	assert resp.text == "a b u"

	request = client.postjson ("http://www.skitai.com/do5/1?a=1", {'b': 1})
	resp = assert_request (vh, request, 200)
	assert resp.text == "a b u"
