import os
from atila import Atila
import skitai

app = Atila (__name__)

app.debug = True
app.use_reloader = True
app.skito_jinja ()

@app.route ("/")
def index (context):
	return context.render ("jinja2overlay.html", name = "Hans Roh", num = 10)

if __name__ == "__main__":
	import skitai

	skitai.mount ("/", 'statics')
	skitai.mount ("/", app)
	skitai.run (
		port = 30371
	)
