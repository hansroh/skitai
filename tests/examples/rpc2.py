from atila import Atila
import time, math
import json
from services import route_guide_pb2

app = Atila (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/add_number")
def add_number (was, a, b):
	return a + b

@app.route ("/")
def index_rpc2 (was, a, b):
	return "<h1>XML-RPC</h1>"
	
if __name__ == "__main__":
	import skitai
	
	skitai.mount ("/rpc2", app)
	skitai.run (port = 30371)
	
