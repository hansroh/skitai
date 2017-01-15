from skitai.saddle import Saddle
import skitai
	

app = Saddle (__name__)
app.use_reloader = True
app.debug = True

@app.route('/')
def index (was):
	return "Hello World by Saddle"
	
if __name__ == "__main__":
	skitai.run (
		address = "127.0.0.1",
		port = 5000,
		mount = ('/', app),
		#certfile = r"C:\skitaid\etc\cert\skitai.com.ca.pem",
		#passphrase = ""
	)
