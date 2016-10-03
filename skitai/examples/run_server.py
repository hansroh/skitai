from skitai.saddle import Saddle
import skitai
	
def app (env, start_response):
	start_response ("200 OK", [("Content-Type", "text/plain")])
	return ['Hello World']

skitaiapp = Saddle (__name__)
skitaiapp.use_reloader = True
skitaiapp.debug = True

@skitaiapp.route('/')
def index (was):
	return "Hello World by Saddle"
	
if __name__ == "__main__":
	skitai.run (
		address = "127.0.0.1",
		port = 5000,
		mount = [
			('/', (__file__, 'app')),
			('/skitai', (__file__, 'skitaiapp'))
		],
		#certfile = r"C:\skitaid\etc\cert\skitai.com.ca.pem",
		#passphrase = ""
	)
