import atila
import skitai

app = atila.Atila (__name__)
@app.route ('/')
def index (was):
    return 'Hello Atila'

if __name__ == '__main__':
    with skitai.preference () as pref:
        skitai.mount ('/', app, pref)
    skitai.run (ip = '127.0.0.1', port = 30371)
