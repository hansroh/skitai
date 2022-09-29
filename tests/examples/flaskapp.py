from flask import Flask, render_template, request
import skitai

app = Flask(__name__)
app.debug = True
app.use_reloader = True
#app.jinja_env = jinjapatch.overlay (__name__)

@app.route ("/3")
def index3 ():
    return 'hello, flask'

if __name__ == "__main__":
    import skitai

    skitai.mount ("/", app)
    skitai.run (port = 30371)
