from atila import Atila
import skitai

app = Atila (__name__)

app.debug = True
app.use_reloader = True
app.jinja_overlay ()

@app.route ("/")
def index (was):
	return "<h1>Skitai Proxy</h1>"



if __name__ == "__main__":
	import skitai

	skitai.set_proxy_keep_alive (55, 605)
	skitai.mount ("/", app)
	skitai.enable_proxy ()
	skitai.run (port = 30371)
