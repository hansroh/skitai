from atila import Atila
import skitai

app = Atila (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/")
def index (context):
	return "Hello"

if __name__ == "__main__":
	import skitai
	import os, sys

	skitai.mount = ('/', app)
	skitai.cron (
		"* * * * *",
		"%s resources%scronjob.py  > resources%scronjob.log 2>&1" % (sys.executable, os.sep, os.sep)
	)
	skitai.enable_smtpda ()
	skitai.run (
		workers = 2,
		port = 30371
	)
