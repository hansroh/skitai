from atila import Atila
import time, math
import json
from services import route_guide_pb2

app = Atila (__name__)
app.securekey = '0123456789'

@app.route ("/")
def index (was):
	return "CSRF: {}".format (was.csrf_token)

@app.route ("/post")
@app.csrf_verification_required
def post (was, **form):
    assert '_csrf_token' in form
    assert not was.session.get ('_csrf_token')
    return 'OK'

@app.route ("/render_or_API")
def documentation (was):
    return was.render_or_API ("documentation.html", content = 'render')


if __name__ == "__main__":
	import skitai
	skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
	skitai.mount ("/", app)
	skitai.mount ("/lb", "@pypi")
	skitai.mount ("/lb2", "@pypi/project")
	skitai.run (port = 30371)
