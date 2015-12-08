#!/usr/bin/python
"""WSGI server example"""
from __future__ import print_function
from gevent.pywsgi import WSGIServer
import codecs

def application(environ, start_response):
	start_response('200 OK', [('Content-Type', 'text/plain')])
	#f = open ("/var/local/skitaid-pub/test/static/test.htm", "rb")	
	#data = f.read ()
	#f.close ()
	data = b"pong"
	return [data]

print('Serving on 5001...')	
WSGIServer(('0.0.0.0', 5001), application, log = codecs.open ("gevent.log", "a", "utf8"), spawn =10000).serve_forever()
