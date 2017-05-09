

if __name__ == "__main__":
	import skitai
	skitai.mount ("/", 'statics')
	skitai.mount ("/", "app.py")
	skitai.mount ("/websocket", 'websocket.py')
	skitai.mount ("/rpc2", 'rpc2.py')
	skitai.mount ("/routeguide.RouteGuide", 'grpc_route_guide.py')
	skitai.mount ("/members", 'auth.py')
	skitai.mount ("/lb", "@pypi")
	skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.python.org")
	skitai.enable_proxy ()
	
	skitai.run (
		threads = 0,
		address = "0.0.0.0",
		port = 5000
	)
