
if __name__ == "__main__":
	import skitai
	import app
	
	skitai.run (		
		address = "0.0.0.0",
		port = 5000,
		clusters = app.clusters,
		mount = app.mount,
		cron = [
			r"* * * * * python3 /home/cronjob.py  > /home/cronjob.log 2>&1"
		]		
	)
