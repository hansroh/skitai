import os
from atila import Atila
import skitai

app = Atila (__name__)

app.debug = True
app.use_reloader = True
app.jinja_overlay ()

@app.route ("/")
def index (was):
	return was.render ("index.html")

@app.route ("/hello")
def hello (was, num = 1):
	was.response ["Content-Type"] = "text/plain"
	return "\n".join (["hello" for i in range (int(num))])

@app.route ("/redirect1")
def redirect1 (was):
	return was.response ("301 Object Moved", "", headers = [("Location", "/redirect2")])

@app.route ("/redirect2")
def redirect2 (was):
	return was.response ("301 Object Moved", "", headers = [("Location", "/")])

@app.route ("/upload")
def upload (was, **karg):
	return was.response ("200 OK", str (karg), headers = [("Content-Type", "text/plain")])

@app.route ("/post")
def post (was, username):
		return 'USER: %s' % username

if __name__ == "__main__":
	import skitai

	skitai.mount ("/", 'statics')
	skitai.mount ("/", app)
	skitai.mount ("/websocket", 'websocket.py')
	skitai.mount ("/rpc2", 'rpc2.py')
	skitai.mount ("/routeguide.RouteGuide", 'grpc_route_guide.py')
	skitai.mount ("/members", 'auth.py')

	skitai.run (
		workers = 3,
		address = "0.0.0.0",
		port = 30371
	)
