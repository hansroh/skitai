#!/usr/bin/python

from skitai.saddle import Saddle
import shutil, os

app = Saddle (__name__)
app.debug = True
app.use_reloader = True

@app.route('/')
def hello_world (was, **form):
	if was.request.command == 'post':		
		file = form ["file1"]
		file.save ("d:\\var\\upload", dup = "o")		
		return str (form)
                            
	return """
  <form action = "/skitai/" enctype="multipart/form-data" method="post">
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

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002)

