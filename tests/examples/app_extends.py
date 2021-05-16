import atila
import atila_vue
import sys
import os
import skitai

os.environ ['SECRET_KEY'] = 'adas'

app = atila.Atila (__name__)
app.set_static ('/statics', 'statics')
app.extends (atila_vue)
app.unroute ('/examples/tutorial', 310)

@app.route ('/')
def index (was):
    return 'Hello Atila'

@app.route ('/examples', methods = ['PUT'])
def examples (was):
    return 'Examples'

if __name__ == '__main__':
    with atila.preference () as pref:
        pref.config.FRONTEND = {}
        skitai.mount ("/", app, pref)
        skitai.run (port = 30371)
