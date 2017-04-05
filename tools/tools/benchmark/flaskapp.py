#!/usr/bin/python

from flask import Flask, request, url_for
import os
from skitai import was

app = Flask(__name__)
app.debug = True
app.use_reloader = True

MULTIPART = """
<form action = "" enctype="multipart/form-data" method="post">
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
<form action = "" method="post">
	<input type="hidden" name="submit-hidden" value="Genious">   
	<p></p>What is your name? <input type="text" name="submit-name" value="Hans Roh"></p>	
	<input type="submit" value="Send"> 
	<input type="reset">
</form>
"""
from flask import Response

@app.route('/stream')
def generate_large_csv():
	def generate():
		for row in range (100):
			yield str(row) + '\n'
	return Response(generate(), mimetype='text/plain')
    

@app.route('/was')
def wastest ():
	s = was.rpc ("http://210.116.122.187:3424/rpc2")
	s.bladese ("adsense.websearch", "computer", 0, 3)
	rs = s.getwait ()	
	return str (rs.data)

@app.route('/', methods=['GET', 'POST'])
def index ():	 
	if request.method == 'POST':		
		if request.files:
			file = request.files ['file1']
			filename = file.filename
			file.save (os.path.join("d:\\var\\upload", filename))
			return os.path.join("d:\\var\\upload", filename)
		else:
			return str (request.form)
	return FORMDATA+"<hr>"+MULTIPART+"<hr>URL_FOR: " + url_for ("generate_large_csv")

@app.route('/ping')
def ping ():
	return "pong"
	
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002)

