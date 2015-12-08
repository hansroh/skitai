def application(environ, start_response):
	status = '200 OK'
	output = b'Pong!'
 
	response_headers = [('Content-type', 'text/plain'),
						('Content-Length', str(len(output)))]
	start_response(status, response_headers)
	return [output]
	
from gevent import wsgi
wsgi.WSGIServer(('', 5001), application, spawn=None).serve_forever()
	