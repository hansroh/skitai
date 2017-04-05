
if __name__ == "__main__":
	import skitai
	import app
	
	skitai.run (
		threads = 0,
		address = "0.0.0.0",
		port = 5000,
		clusters = app.clusters,
		mount = app.mount		
	)
