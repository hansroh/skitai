#-*- coding: utf8 -*-

from skitai.server import ssgi
app = ssgi.Application (__name__)
app.set_devel ()

@app.route ("/")
def info (was, f = ""):
	return '<h1>Hello, World</h1><a href="/">Home</a>'


	
