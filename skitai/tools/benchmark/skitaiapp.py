#!/usr/bin/python

from skitai.saddle import Saddle
app = Saddle (__name__)
app.debug = True
app.use_reloader = True

@app.route('/')
def hello_world (was):
	return 'pong4sdfdd55'

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002)

