import atila
import asyncio

app = atila.Atila (__name__)
@app.route ('/')
async def index (context):
    await asyncio.sleep ()
    return 'Hello Atila'

if __name__ == '__main__':
    with atila.preference () as pref:
        app.mount ('/statics', 'statics')
        app.run ('127.0.0.1', 30371, pref = pref, mount = '/')
