
if __name__ == "__main__":
	import skitai
	import app
	
	skitai.run (
		address = "0.0.0.0",
		port = 5000,
		clusters = app.clusters,
		mount = app.mount,
		certfile = r"C:\skitaid\etc\certifications\example.pem",
		keyfile = r"C:\skitaid\etc\certifications\example.key",
		passphrase = "fatalbug"
	)
