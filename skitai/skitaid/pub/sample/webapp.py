from skitai.saddle import Saddle
import skitai

app = Saddle (__name__)

app.debug = True
app.use_reloader = True

#app.authorization = "digest"
#app.realm = "Test"
#app.user = "app"
#app.password = "1111"


@app.route ("/")
def index (was):	
	return was.render ("index.html")

@app.route ("/documentation")
def documentation (was):
	req = was.get ("https://pypi.python.org/pypi/skitai")
	pypi_content = (
			"<h4>"
			"<p>It seems some problem at <a href='https://pypi.python.org/pypi/skitai'>PyPi</a>.</p>"
			"</h4>"	
			"<p>Please visit <a href='https://pypi.python.org/pypi/skitai'> https://pypi.python.org/pypi/skitai</a></p>"
		)
	
	rs = req.getwait (10)
	if rs.data	:
		content = rs.data.decode ("utf8")
		s = content.find ('<div class="section">')
		if s != -1:		
			e = content.find ('<a name="downloads">', s)
			if e != -1:						
				pypi_content = "<h4>This contents retrieved right now using skitai was service from <a href='https://pypi.python.org/pypi/skitai'> https://pypi.python.org/pypi/skitai</a></h4>" + content [s:e]
	
	return was.render ("documentation.html", content = pypi_content)


@app.route ("/hello")
def hello (was, num = 1):
	was.response ["Content-Type"] = "text/plain"
	return "\n".join (["hello" for i in range (int(num))])

@app.route ("/websocket/echo")
def echo (was, message = ""):
	if "websocket_init" in was.env:
		was.env ["websocket_init"] = (skitai.WEBSOCKET_REQDATA, 60, "message")
		return ""
	return "ECHO:" + message

@app.route ("/websocket/talk")
def talk (was, name = "Hans Roh"):
	if "websocket_init" in was.env:
		was.env ["websocket_init"] = (skitai.WEBSOCKET_DEDICATE, 60, None)
		return ""
	
	ws = was.env ["websocket"]
	while 1:
		messages = ws.getswait (10)
		if messages is None:
			break	
		for m in messages:
			if m.lower () == "bye":
				ws.send ("Bye, have a nice day." + m)
				ws.close ()
				break
			elif m.lower () == "hello":
				ws.send ("Hello, " + name)				
			else:	
				ws.send ("You Said:" + m)


@app.route ("/websocket/chat")
def chat (was, roomid):
	if "websocket_init" in was.env:
		was.env ["websocket_init"] = (skitai.WEBSOCKET_MULTICAST, 60, "roomid")
		return ""
	
	ws = was.env ["websocket"]	
	while 1:
		messages = ws.getswait (10)
		if messages is None:
			break	
		for client_id, m in messages:
			ws.sendall ("Client %d Said: %s" % (client_id, m))

@app.route ("/websocket")
def websocket (was, mode = "echo"):
	if mode == "talk":
		mode += "?name=Hans"
	elif mode == "chat":	
		mode += "?roomid=1"
	return was.render ("websocket.html", path = mode)
	
"""
# Flask

from flask import Flask, request
import skitai

app = Flask (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/echo")
def wsecho ():
	was = skitai.was
	if "websocket_init" in request.environ:
		request.environ ["websocket_init"] = (skitai.WEBSOCKET_REQDATA, 60, "message")
		return ""
	return "ECHO:" + request.args.get('message', '')
"""

