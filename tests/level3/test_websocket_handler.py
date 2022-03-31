from confutil import rprint
import confutil
from skitai.testutil import offline as testutil
from skitai.handlers import vhost_handler
import skitai
import os

def test_websocket_handler (wasc, app, client):
	@app.route ("/echo")
	def echo (was, message):
		if was.wsinit ():
			return was.wsconfig (skitai.WS_SIMPLE, 60)
		elif was.wsopened ():
			return "Welcome Client %s" % was.wsclient ()
		elif was.wshasevent (): # ignore the other events
			return
		was.websocket.send ("You said," + message)
		was.websocket.send ("acknowledge")

	@app.route ("/chat")
	def chat (was, message, roomid):
		if was.wsinit ():
			return was.wsconfig (skitai.WS_GROUPCHAT, 60)
		elif was.wsopened ():
			return "Client %s has entered" % was.wsclient ()
		elif was.wsclosed ():
			return "Client %s has leaved" % was.wsclient ()
		return "Client %s Said: %s" % (was.wsclient (), message)

	vh = testutil.install_vhost_handler ()
	root = confutil.getroot ()
	pref = skitai.pref ()
	vh.add_route ("default", ("/ws", app, root), pref)
	app.access_control_allow_origin = ["http://www.skitai.com:80"]

	# WEBSOCKET
	testutil.enable_threads ()
	resp = client.ws ("http://www.skitai.com/ws/echo", "Hello")
	assert resp.status_code == 101

	resp = client.ws ("http://www.skitai.com/ws/chat", "Hello")
	assert resp.status_code == 400
	resp = client.ws ("http://www.skitai.com/ws/chat?roomid=1", "Hello")
	assert resp.status_code == 101

	testutil.disable_threads ()
	resp = client.ws ("http://www.skitai.com/ws/echo", "Hello")
	assert resp.status_code == 101
	resp = client.ws ("http://www.skitai.com/ws/chat?roomid=1", "Hello")
	assert resp.status_code == 101

