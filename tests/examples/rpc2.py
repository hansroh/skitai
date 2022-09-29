from atila import Atila
import time, math
import json
try:
    from services import route_guide_pb2
except ImportError:
    from services import route_guide_pb2_v3 as route_guide_pb2

app = Atila (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/add_number")
def add_number (context, a, b):
	return a + b

@app.route ("/")
def index_rpc2 (context, a, b):
	return "<h1>XML-RPC</h1>"

if __name__ == "__main__":
	import skitai

	skitai.mount ("/rpc2", app)
	skitai.run (port = 30371)

