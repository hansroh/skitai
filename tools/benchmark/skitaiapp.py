#!/usr/bin/python

from skitai.saddle import Saddle
import shutil, os

app = Saddle (__name__)
app.debug = True
app.use_reloader = True

app.securekey = "iodfjksdfkjsdhkfjsd0987987sdf"
app.realm = "Skitai API"
app.user = "app"
app.password = "1111"
app.authorization = "digest"

MULTIPART = """
<form action = "/" enctype="multipart/form-data" method="post">
	<input type="hidden" name="submit-hidden" value="Genious">   
	<p></p>What is your name? <input type="text" name="submit-name" value="Hans Roh"></p>
	<p></p>What files are you sending? <br />
	<input type="file" name="file1"><br />
	<input type="file" name="file2">
	</p>
	<input type="submit" value="Send"> 
	<input type="reset">
</form>
"""

FORMDATA = """
<form action = "/" method="post">
	<input type="hidden" name="submit-hidden" value="Genious">   
	<p></p>What is your name? <input type="text" name="submit-name" value="Hans Roh"></p>	
	<input type="submit" value="Send"> 
	<input type="reset">
</form>
"""
import skitaipackage

app.mount ("/", skitaipackage, "package")

@app.route ("/fancy/<int:cid>/<cname>")
def fancy (was, cid, cname, zipcode):
	return [
	"%s - %s (%s)" % (cid, cname, zipcode),
	"<hr />",
	was.ab ("fancy", 200, "Skitai Inc", "31052")
	]

@app.route('/')
def hello_world (was, **form):
	if was.request.command == 'post':		
		file = form.get ("file1")
		if file:
			file.save ("d:\\var\\upload", dup = "o")
		return str (form)
	return [was.ab ("fancy", 200, "Skitai Inc", "31052"), FORMDATA, "<hr />", MULTIPART]

@app.route('/indians')
def hello_world (was, num = 8):
	if was.request.command == 'get':		
		was.response ["Content-Type"] = "text/xml"
		return was.toxml ((num,))
	else:
		return num	

@app.route('/ping')
def ping (was, **form):
	return "pong"

	
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002)

