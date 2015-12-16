from skitai.saddle import Saddle
app = Saddle (__name__)

app.debug = True
app.use_reloader = True

@app.route ("/")
def index (was):
	req = was.get ("https://pypi.python.org/pypi/skitai")
	t = was.app.get_template ("index.html")	
	pypi_content = (
			"<h4>"
			"<p>It seems some problem at <a href='https://pypi.python.org/pypi/skitai'>PyPi</a>.</p>"
			"</h4>"	
			"<p>Please visit <a href='https://pypi.python.org/pypi/skitai'> https://pypi.python.org/pypi/skitai</a></p>"
		)
	
	rs = req.getwait (10)	
	if rs.data	:
		content = rs.data.decode ("utf8")
		s = content.find ('<div class="section">')
		if s != -1:		
			e = content.find ('<a name="downloads">', s)
			if e != -1:						
				pypi_content = "<h4>This contents retrieved right now using skitai was service from <a href='https://pypi.python.org/pypi/skitai'> https://pypi.python.org/pypi/skitai</a></h4>" + content [s:e]
		
	return t.render ({"content": pypi_content})


@app.route ("/hello")
def hello (was, num = 1):
	was.response ["Content-Type"] = "text/plain"
	return "\n".join (["hello" for i in range (int(num))])
