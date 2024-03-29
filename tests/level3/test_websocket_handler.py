from confutil import rprint
import confutil
from skitai.testutil import offline as testutil
from skitai.handlers import vhost_handler
import skitai
import os

def test_websocket_handler (Context, app, client):
	@app.route ("/echo")
	def echo (context, message):
		if context.wsinit ():
			return context.wsconfig (skitai.WS_SIMPLE, 60)
		elif context.wsopened ():
			return "Welcome Client %s" % context.wsclient ()
		elif context.wshasevent (): # ignore the other events
			return
		context.stream.send ("You said," + message)
		context.stream.send ("acknowledge")

	vh = testutil.install_vhost_handler ()
	root = confutil.getroot ()
	pref = skitai.pref ()
	vh.add_route ("default", ("/ws", app, root), pref)
	app.access_control_allow_origin = ["http://www.skitai.com:80"]

	# WEBSOCKET
	testutil.enable_threads ()
	resp = client.ws ("http://www.skitai.com/ws/echo", "Hello")
	assert resp.status_code == 101

	testutil.disable_threads ()
	resp = client.ws ("http://www.skitai.com/ws/echo", "Hello")
	assert resp.status_code == 101
