import atila

app = atila.Atila (__name__)
@app.route ('/')
def index (was):
    return 'Hello Atila'

if __name__ == '__main__':
    with atila.preference () as pref:
        app.mount ('/statics', 'statics')
        app.run ('127.0.0.1', 30371, pref = pref, mount = '/')
