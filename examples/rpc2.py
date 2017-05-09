from skitai.saddle import Saddle
import time, math
import json
from package import route_guide_pb2

app = Saddle (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/add_number")
def RouteChat (was, a, b):
	return a + b

@app.route ("/")
def RouteChat (was, a, b):
	return "<h1>XML-RPC</h1>"
	
if __name__ == "__main__":
	import skitai
	
	skitai.mount ("/rpc2", app)
	skitai.run ()
	
