from atila import Atila

if __name__ == "__main__":
	import skitai
	skitai.mount ("/", "app.py")
	skitai.enable_forward (12443, 30371, '127.0.0.1')
	skitai.enable_ssl (
		"resources/certifications/server.crt",
		"resources/certifications/server.key",
		"fatalbug"
	)
	skitai.run (port = 30371, workers = 1)
