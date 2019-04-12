from atila import Atila
import time, math
import json
from package import route_guide_pb2

app = Atila (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/")
def RouteChat (was):
	return "<h1>Reverse Proxing</h1><a href='/lb/pypi'>Click Here</a>"

@app.route ("/pypi")
def documentation (was):
    return was.get ("https://pypi.org/project/rs4/", headers = [("Accept", "text/html")]).fetch ()

if __name__ == "__main__":
	import skitai
	
	skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
	skitai.mount ("/", app)
	skitai.mount ("/lb", "@pypi")
	skitai.mount ("/lb2", "@pypi/project")
	skitai.run (port = 30371)
