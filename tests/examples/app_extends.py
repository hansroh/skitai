import atila
import atila_vue
import sys
import os
import skitai

os.environ ['SECRET_KEY'] = 'adas'

app = atila.Atila (__name__)
app.set_static ('/statics', 'statics')
app.extends (atila_vue)

@app.route ('/')
def index (was):
    return 'Hello Atila'

if __name__ == '__main__':
    with atila.preference () as pref:
        skitai.mount ("/", app, pref)
        skitai.run (port = 30371)
