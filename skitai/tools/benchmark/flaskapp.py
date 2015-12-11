#!/usr/bin/python

from flask import Flask, request
import os

app = Flask(__name__)
app.debug = True
app.use_reloader = True

@app.route('/', methods=['GET', 'POST'])
def hello_world():	 
	if request.method == 'POST':		
		file = request.files ['file1']
		filename = file.filename
		file.save (os.path.join("d:\\var\\upload", filename))
		return os.path.join("d:\\var\\upload", filename)
                            
	return """
  <form action = "/flask/" enctype="multipart/form-data" method="post">
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

