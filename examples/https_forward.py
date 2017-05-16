
if __name__ == "__main__":
	import skitai
	skitai.mount ("/", "app.py")
	skitai.enable_forward (80, 443)
	skitai.enable_ssl (
		"resources/certifications/server.crt",
		"resources/certifications/server.key",
		"fatalbug"
	)
	skitai.run (port = 443, workers = 2)
