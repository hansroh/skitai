import os
from skitai.saddle import Saddle
import skitai

app = Saddle (__name__)

app.debug = True
app.use_reloader = True
app.skito_jinja ()

@app.route ("/")
def index (was):	
	return was.render ("jinja2overlay.html", name = "Hans Roh", num = 10)

if __name__ == "__main__":
	import skitai	
	
	skitai.mount ("/", 'statics')
	skitai.mount ("/", app)			
	skitai.run ()