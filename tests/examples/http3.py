from atila import Atila

if __name__ == "__main__":
	import skitai

	skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
	skitai.mount ("/", 'statics')
	skitai.mount ("/", "app.py")
	skitai.mount ("/websocket", 'websocket.py')
	skitai.mount ("/rpc2", 'rpc2.py')
	skitai.mount ("/routeguide.RouteGuide", 'grpc_route_guide.py')
	skitai.mount ("/members", 'auth.py')
	skitai.mount ("/lb", "@pypi")
	skitai.enable_ssl (
		"resources/certifications/server.crt",
		"resources/certifications/server.key",
		"fatalbug"
	)
	skitai.run (port = 30371, quic = 4433)
