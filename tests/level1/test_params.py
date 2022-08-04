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

def mount (app):
	def z (context):
		k = list (context.request.args.keys ())
		k.sort ()
		return " ".join (k)

	@app.route ("/do", methods = ["GET", "POST"])
	def index (context):
		return z (context)

	@app.route ("/do2", methods = ["GET", "POST"])
	def index2 (context, a):
		return z (context)

	@app.route ("/do3/<u>", methods = ["GET", "POST"])
	def index3 (context, **args):
		return z (context)

	@app.route ("/do4/<u>", methods = ["GET", "POST"])
	def index4 (context, u, a, b):
		return z (context)

	@app.route ("/do5/<u>", methods = ["GET", "POST"])
	def index5 (context, u, a):
		return z (context)

	@app.route ("/do6", methods = ["GET", "POST"])
	def index6 (context, a):
		return z (context)


def test_params (app, client):
	global CLIENT
	CLIENT = client

	mount (app)
	app.restrict_parameter_count = False

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


def test_params_restrict (app, client):
	global CLIENT
	CLIENT = client

	mount (app)
	app.restrict_parameter_count = True

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
	resp = assert_request (vh, request, 400)

	request = client.post ("http://www.skitai.com/do", {'a': 1})
	resp = assert_request (vh, request, 400)

	request = client.postjson ("http://www.skitai.com/do", {'a': 1})
	resp = assert_request (vh, request, 400)

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
	resp = assert_request (vh, request, 400)

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
	resp = assert_request (vh, request, 400)

	request = client.postjson ("http://www.skitai.com/do5/1?a=1", {'b': 1})
	resp = assert_request (vh, request, 400)
