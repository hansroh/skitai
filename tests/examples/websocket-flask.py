from flask import Flask, render_template, request
import skitai

app = Flask(__name__)
app.debug = True
app.use_reloader = True
#app.jinja_env = jinjapatch.overlay (__name__)

@app.route ("/echo")
def echo ():
	event = request.environ.get ("websocket.event")
	if event == skitai.WS_EVT_INIT:
		request.environ ["websocket.config"] = (skitai.WS_SIMPLE, 60, ("message",))
		return ""
	elif event == skitai.WS_EVT_OPEN:
		return 'Welcome Client 0'
	elif event:
		return ''
	request.environ ["websocket"].send ('1st: ' + request.args.get ("message", ""))
	return "2nd: " + request.args.get ("message", "")

def onopen ():
	return  'Welcome Client 0'

@app.route ("/echo2")
@skitai.websocket ("message", onopen = onopen)
def echo2 ():
	request.environ ["websocket"].send ('1st: ' + request.args.get ("message", ""))
	return "2nd: " + request.args.get ("message", "")

@app.route ("/echo3")
@skitai.websocket ()
def echo3 ():
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

@app.route ("/")
def websocket ():
	mode = request.args.get('mode', '')
	if mode == "chat":
		mode += "?room_id=1"
	elif mode == "multi":
		mode += "?room_id=2"
	return render_template ("websocket-flask.html", path = mode)

if __name__ == "__main__":
	import skitai

	skitai.mount ("/websocket", app)
	skitai.run (port = 30371)
