from skitai.saddle import Saddle
import skitai

app = Saddle (__name__)

app.access_control_allow_origin = ["*"]
app.debug = True
app.use_reloader = True
app.jinja_overlay ()

@app.route ("/echo-single")
def echo_single (was, message):
	# return a single message, use aquests.ws (DO NOT USE /echo)
	if was.wsinit ():
		return was.wsconfig (skitai.WS_SIMPLE, 60)
	elif was.wshasevent (): # ignore the other events
		return
	return "You said," + message
	
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
def chat (was, message, room_id):
	if was.wsinit ():
		return was.wsconfig (skitai.WS_GROUPCHAT, 60)
	elif was.wsopened ():
		return "Client %s has entered" % was.wsclient ()
	elif was.wsclosed ():
		return "Client %s has leaved" % was.wsclient ()
	return "Client %s Said: %s" % (was.wsclient (), message)
		
@app.route ("/")
def websocket (was, mode = "echo"):
	if mode == "chat":	
		mode += "?room_id=1"
	return was.render ("websocket.html", path = mode)
	
if __name__ == "__main__":
	import skitai
	
	skitai.mount ("/websocket", app)
	skitai.run ()
	