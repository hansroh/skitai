from atila import Atila
import skitai

app = Atila (__name__)

app.access_control_allow_origin = ["*"]
app.debug = True
app.use_reloader = True
app.jinja_overlay ()
app.securekey = 'asdadada'

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

def onopen (was):
	return  'Welcome Client 0'

@app.route ("/echo2")
@app.websocket (skitai.WS_SIMPLE | skitai.WS_NQ, 60, onopen = onopen)
def echo2 (was, message):
	was.websocket.send ('1st: ' + message)
	return "2nd: " + message

@app.route ("/echo3")
@app.websocket (skitai.WS_SIMPLE | skitai.WS_NQ, 60, onopen = onopen)
def echo3 (was, message):
	was.websocket.send ('1st: ' + message)
	return "2nd: " + message

@app.route ("/echo4")
@app.websocket (skitai.WS_SIMPLE | skitai.WS_SESSION, 60)
def echo4 (was):
	n = 0
	while 1:
		n += 1
		msg = yield
		if n == 1:
			yield '1st: ' + msg
		elif n == 2:
			yield '2nd: ' + msg
		else:
			yield 'many: ' + msg

def onopenp (was):
  was.session.set ("WS_ID", was.websocket.client_id)

def onclosep (was):
  was.session.remove ("WS_ID")

@app.route ("/push")
@app.websocket (skitai.WS_SIMPLE, 1200, onopenp, onclosep)
def push (was, message):
  return 'you said: ' + message

@app.route ("/wspush")
def ws_push (was):
	was.session.set ("WS_ID", 0)
	app.websocket_send (
      	was.session.get ("WS_ID"),
       "Item In Stock!"
	)
	return "Sent"

@app.route ("/chat")
def chat (was, message, room_id):
	if was.wsinit ():
		return was.wsconfig (skitai.WS_GROUPCHAT, 60)
	elif was.wsopened ():
		return "Client %s has entered" % was.wsclient ()
	elif was.wsclosed ():
		return "Client %s has leaved" % was.wsclient ()
	return "Client %s Said: %s" % (was.wsclient (), message)

def onchatopen (was):
	return "Client %s has entered" % was.wsclient ()

def onchatclose (was):
	return "Client %s has leaved" % was.wsclient ()

@app.route ("/chat2")
@app.websocket (skitai.WS_GROUPCHAT, 60, onopen = onchatopen, onclose = onchatclose)
def chat2 (was, message, room_id):
	if message:
		return "Client %s Said: %s" % (was.wsclient (), message)

@app.route ("/")
def websocket (was, mode = "echo"):
	if mode == "chat":
		mode += "?room_id=1"
	return was.render ("websocket.html", path = mode)

if __name__ == "__main__":
	import skitai

	skitai.mount ("/websocket", app)
	skitai.run (port = 30371)
