import os
from atila import Atila
import skitai

if os.name == "nt":
	from skitai.win32service import ServiceFramework
	class ServiceConfig (ServiceFramework):
		_svc_name_ = "SAE_EXAMPLE"
		_svc_display_name_ = "Skitai Example Service"
		_svc_app_ = __file__
		_svc_python_ = r"c:\python34\python.exe"

app = Atila (__name__)
app.debug = True
app.use_reloader = True
app.jinja_overlay ()

app.realm = "Secured Area"
app.users = {"admin": ("1111", 0, {'role': 'root'})}
app.authenticate = None

@app.route ("/")
def index (was):	
	return was.render ("index.html")

@app.route ("/dnserror")
def dnserror (was):
	req = was.get ("https://pypi.python.orgx/pypi/skitai")
	rs = req.getwait (10)
	return "%d %d %s" % (rs.status, rs.status_code, rs.reason)

@app.route ("/documentation")
def documentation (was):
	req = was.get ("https://pypi.org/project/skitai/")
	pypi_content = "<h4><p>It seems some problem at <a href='https://pypi.python.org/pypi/skitai'>PyPi</a>.</p></h4><p>Please visit <a href='https://pypi.python.org/pypi/skitai'> https://pypi.python.org/pypi/skitai</a></p>"	
	rs = req.getwait (10)
	if rs.data:
		content = rs.data.decode ("utf8")
		s = content.find ('<div class="project-description">')
		if s != -1:		
			e = content.find ('<div id="history"', s)
			if e != -1:						
				pypi_content = "<h4>This contents retrieved right now using skitai was service from <a href='https://pypi.python.org/pypi/skitai'> https://pypi.python.org/pypi/skitai</a></h4>" + content [s:e]	
	return was.render ("documentation.html", content = pypi_content)

def handle_response (promise, rs):
	pypi_content = "<h3>Error</h3>"
	if rs.data:
		content = rs.data.decode ("utf8")
		s = content.find ('<div class="project-description">')
		if s != -1:
			e = content.find ('<div id="history"', s)
			if e != -1:						
				content = "<h4>This contents retrieved right now using skitai was service from <a href='https://pypi.python.org/pypi/skitai'> https://pypi.python.org/pypi/skitai</a></h4>" + content [s:e]		
		promise [rs.id]	= content		
	if promise.fulfilled ():
		promise.settle (promise.render ("documentation2.html"))
		
@app.route ("/documentation2")
def documentation2 (was):
	promise = was.promise (handle_response)
	promise.get ('skitai', "https://pypi.org/project/skitai/")
	return promise
	
@app.route ("/hello")
def hello (was, num = 1):
	was.response ["Content-Type"] = "text/plain"
	return "\n".join (["hello" for i in range (int(num))])
	
@app.route ("/redirect0")
def redirect0 (was):	
	return ""
	
@app.route ("/redirect1")
def redirect1 (was):	
	return was.response ("301 Object Moved", "", headers = [("Location", "/redirect2")])

@app.route ("/redirect2")
def redirect2 (was):
	return was.response ("301 Object Moved", "", headers = [("Location", "/")])

@app.route ("/upload")
def upload (was, **karg):
	return was.response ("200 OK", str (karg), headers = [("Content-Type", "text/plain")])

@app.route ("/post")
def post (was, username):	
	return 'USER: %s' % username

@app.route ("/test")
def test (was):
	was.response ["Content-Type"] = "text/plain"
	return str (was.request.args)

@app.route ("/json")
def json (was):
	return was.response.api (data = "JSON")


if __name__ == "__main__":
	import skitai		
	
	if os.name == "nt":		
		skitai.set_service (ServiceConfig)
		
	skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.python.org")
	skitai.mount ("/", 'statics')
	skitai.mount ("/", app)
	skitai.mount ("/websocket", 'websocket.py')
	skitai.mount ("/rpc2", 'rpc2.py')
	skitai.mount ("/routeguide.RouteGuide", 'grpc_route_guide.py')
	skitai.mount ("/members", 'auth.py')
	skitai.mount ("/lb", "@pypi")
	skitai.enable_proxy ()

	skitai.run (
		port = 30371,
		workers = 1,
		threads = 4				
	)
	
