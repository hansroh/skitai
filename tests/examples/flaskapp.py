from flask import Flask, render_template, request
import skitai
from skitai import was

app = Flask(__name__)
app.debug = True
app.use_reloader = True
#app.jinja_env = jinjapatch.overlay (__name__)

@app.route ("/")
def index ():
    reqs = [
        was.get ("@pypi/project/rs4/", headers = {"Accept": "*/*"}),
    ]
    tasks = was.Tasks (reqs).fetch ()
    return str (tasks)

@app.route ("/2")
def index2 ():
    def respond (was, rss):
            return was.response.API (status_code = [rs.status_code for rs in rss.dispatch ()], a = rss.a)
    reqs = [
        was.get ("@pypi/project/rs4/", headers = {"Accept": "*/*"}),
    ]
    return was.Tasks (reqs, a = 100).then (respond)

@app.route ("/3")
def index3 ():
    return 'hello, flask'

if __name__ == "__main__":
    import skitai

    skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
    skitai.mount ("/", app)
    skitai.run (port = 30371)
