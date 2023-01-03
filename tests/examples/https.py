from atila import Atila

if __name__ == "__main__":
	import skitai

	skitai.mount ("/", 'statics')
	skitai.mount ("/", "app.py")
	skitai.mount ("/websocket", 'websocket-atila.py')
	skitai.mount ("/rpc2", 'rpc2.py')
	skitai.mount ("/routeguide.RouteGuide", 'grpc_route_guide.py')
	skitai.mount ("/members", 'auth.py')
	skitai.enable_ssl (
		"resources/certifications/server.crt",
		"resources/certifications/server.key",
		"fatalbug"
	)
	skitai.set_503_estimated_timeout (0)
	skitai.run (port = 30371)
