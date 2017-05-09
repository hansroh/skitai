from skitai.saddle import Saddle
import time, math
import json
from package import route_guide_pb2

app = Saddle (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/")
def RouteChat (was):
	return "<h1>Reverse Proxing</h1><a href='/lb/proxed'>Click Here</a>"

@app.route ("/proxed")
def RouteChat (was):
	return "<h1>Reverse Proxed</h1><a href='/lb/'>Click Here</a>"
	
if __name__ == "__main__":
	import skitai
	
	skitai.alias ("@pypi", skitai.PROTO_HTTP, "pypi.python.org")
	skitai.mount ("/", app)
	skitai.mount ("/lb", "@pypi")
	skitai.run ()
