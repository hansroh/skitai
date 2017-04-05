import os
from skitai.saddle import Saddle
import skitai

app = Saddle (__name__)

app.debug = True
app.use_reloader = True
app.skito_jinja_overlay ()

@app.route ("/")
def index (was):	
	return was.render ("jinja2overlay.html", name = "Hans Roh", num = 10)

if __name__ == "__main__":
	import skitai	
	
	skitai.run (
		address = "0.0.0.0",
		port = 5000,		
		mount = [				
			("/", 'static'),
			("/", app),
		]		
	)
