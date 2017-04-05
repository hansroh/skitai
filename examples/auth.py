from skitai.saddle import Saddle
import skitai

app = Saddle (__name__)

app.debug = True
app.use_reloader = True
app.jinja_overlay ()

app.authorization = "digest"
app.authenticate = True
app.realm = "Secured Area"
app.users = {"admin": ("1111", 0, {'role': 'root'})}
app.authenticate = False

@app.route ("/", authenticate = 1)
def index (was):	
	return was.render ("index.html")


if __name__ == "__main__":
	import skitai
	skitai.run (
		mount = ("/", app)
	)
	