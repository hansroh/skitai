
if __name__ == "__main__":
	import skitai
	
	skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.python.org")
	skitai.mount ("/", 'statics')
	skitai.mount ("/", app)
	skitai.mount ("/websocket", 'websocket.py')
	skitai.mount ("/rpc2", 'rpc2.py')
	skitai.mount ("/routeguide.RouteGuide", 'grpc_route_guide.py')
	skitai.mount ("/members", 'auth.py')
	skitai.mount ("/lb", "@pypi")
	skitai.enable_ssl (
		"reosurces/certifications/example.pem",
		"reosurces/certifications/example.key",
		"fatalbug"
	)
	skitai.run ()
