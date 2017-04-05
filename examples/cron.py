from skitai.saddle import Saddle
import skitai

app = Saddle (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/")
def index (was):	
	return "Hello"
	
if __name__ == "__main__":
	import skitai	
	import os, sys
	
	skitai.run (
		mount = [('/', app)],
		cron = [
			r"* * * * * %s resources%scronjob.py  > resources%scronjob.log 2>&1" % (sys.executable, os.sep, os.sep)
		]
	)
	