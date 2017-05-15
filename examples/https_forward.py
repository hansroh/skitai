
if __name__ == "__main__":
	import skitai
	skitai.mount ("/", "app.py")
	skitai.enable_forward (80, 5000)
	skitai.enable_ssl (
		"resources/certifications/example.pem",
		"resources/certifications/example.key",
		"fatalbug"
	)
	skitai.run ()
