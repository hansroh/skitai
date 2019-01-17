from atila import Atila
import skitai

app = Atila (__name__)

app.debug = True
app.use_reloader = True
app.jinja_overlay ()
app.realm = "Secured Area"
app.users = {"admin": ("1111", 0, {'role': 'root'})}

@app.route ("/", authenticate = "digest")
def index (was):	
	return was.render ("index.html")

if __name__ == "__main__":
	import skitai
	skitai.mount ("/", app)
	skitai.run (
		address = "0.0.0.0",
		port = 30371	
	)
	