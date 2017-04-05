from skitai.saddle import Saddle
import skitai

app = Saddle (__name__)

app.debug = True
app.use_reloader = True
app.jinja_overlay ()

@app.route ("/")
def index (was):	
	return "<h1>Skitai Proxy</h1>"

if __name__ == "__main__":
	import skitai
	skitai.run (
		mount = ("/", app),
		proxy = 1
	)
	