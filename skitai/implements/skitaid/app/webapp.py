#-*- coding: utf8 -*-

from skitai.server import ssgi

app = ssgi.Application (__name__)
app.set_devel (True)
	
@app.route ("/hello")
def hello (was):
	return '<h1>Hello World</h1>'
	
